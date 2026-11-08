#pragma once
// Stage 3D-06-P3: SPD multi-color block symmetric Gauss-Seidel (SSOR omega=1).
// C++20, standalone header, optional OpenMP, 3 DOF per mesh vertex.
// No modification to the mechanical model or the assembled coefficients.
#include <array>
#include <algorithm>
#include <cstdint>
#include <cmath>
#include <stdexcept>
#include <vector>

namespace stage3d06::p3 {

struct Workspace {
    // Reused per FEM solver/BCSR instance; not shared between simultaneous PCG solves.
    std::vector<double> y, dy;
};

struct Coloring {
    std::vector<int> color_of_node;
    std::vector<int> offsets; // offsets[c], offsets[c+1]: nodes of color c
    std::vector<int> vertices;
    // Precomputed BCSR positions in original ascending per-row order.
    // Built once for an immutable graph; reused across all Newton/PCG steps.
    std::vector<int> lower_offsets, upper_offsets;
    std::vector<int> lower_positions, upper_positions;
    int count() const noexcept { return offsets.empty() ? 0 : int(offsets.size())-1; }
};

// A deterministic distance-one greedy coloring of the block adjacency graph.
// The original BCSR row order is preserved. Colors impose a NEW symmetric
// block ordering: same-colored nodes are independent, and can run in parallel.
inline Coloring build_coloring(int n, const std::vector<int>& row, const std::vector<int>& col) {
    if (n < 0 || row.size() != size_t(n+1) || row.front()!=0 ||
        row.back()!=int(col.size())) throw std::runtime_error("P3: invalid BCSR graph");
    Coloring out;
    out.color_of_node.assign(size_t(n),-1);
    std::vector<int> used(1,-1);
    int ncolors=0;
    for(int i=0;i<n;++i){
        if(row[i]>row[i+1]) throw std::runtime_error("P3: non-monotone row pointers");
        for(int p=row[i];p<row[i+1];++p){
            const int j=col[p];
            if(j<0 || j>=n) throw std::runtime_error("P3: column index out of range");
            if(j==i || out.color_of_node[j]<0) continue;
            const int c=out.color_of_node[j];
            if(c>=int(used.size())) used.resize(size_t(c+1),-1);
            used[c]=i;
        }
        int chosen=0;
        while(chosen<int(used.size()) && used[chosen]==i) ++chosen;
        if(chosen==int(used.size())) used.push_back(-1);
        out.color_of_node[i]=chosen;
        ncolors=std::max(ncolors,chosen+1);
    }
    // Reject invalid unsymmetric adjacency or a same-color graph edge.
    // The graph is structurally symmetric for Tet10 stiffness.
    for(int i=0;i<n;++i)
        for(int p=row[i];p<row[i+1];++p)
            if(col[p]!=i && out.color_of_node[i]==out.color_of_node[col[p]])
                throw std::runtime_error("P3: coloring has a conflicting edge");
    out.offsets.assign(size_t(ncolors+1),0);
    for(int c:out.color_of_node) ++out.offsets[size_t(c+1)];
    for(int c=0;c<ncolors;++c)out.offsets[c+1]+=out.offsets[c];
    out.vertices.resize(size_t(n));
    auto next=out.offsets;
    for(int i=0;i<n;++i)out.vertices[size_t(next[out.color_of_node[i]]++)]=i;
    out.lower_offsets.assign(size_t(n+1),0);
    out.upper_offsets.assign(size_t(n+1),0);
    for(int i=0;i<n;++i){
        const int ci=out.color_of_node[i];
        for(int pp=row[i];pp<row[i+1];++pp){
            const int cj=out.color_of_node[col[pp]];
            if(cj<ci) ++out.lower_offsets[size_t(i+1)];
            else if(cj>ci) ++out.upper_offsets[size_t(i+1)];
        }
    }
    for(int i=0;i<n;++i){
        out.lower_offsets[size_t(i+1)]+=out.lower_offsets[size_t(i)];
        out.upper_offsets[size_t(i+1)]+=out.upper_offsets[size_t(i)];
    }
    out.lower_positions.resize(size_t(out.lower_offsets.back()));
    out.upper_positions.resize(size_t(out.upper_offsets.back()));
    auto il=out.lower_offsets, iu=out.upper_offsets;
    for(int i=0;i<n;++i){
        const int ci=out.color_of_node[i];
        for(int pp=row[i];pp<row[i+1];++pp){
            const int cj=out.color_of_node[col[pp]];
            if(cj<ci) out.lower_positions[size_t(il[size_t(i)]++)]=pp;
            else if(cj>ci) out.upper_positions[size_t(iu[size_t(i)]++)]=pp;
        }
    }
    return out;
}

// The 3x3 diagonal inverses must be built from the projected blocks: each
// constrained DOF has its row/column zeroed and diagonal set to 1 before inversion.
// The rhs and solution in these coordinates are forced to zero, preserving the
// invariant required by the P2 projected SpMV.
inline void apply(const Coloring& colors, int n,
    const std::vector<int>& row, const std::vector<int>& col,
    const std::vector<std::array<double,9>>& a,
    const std::vector<std::array<double,9>>& invdiag,
    const std::vector<int>& diag,
    const std::vector<double>& rhs, std::vector<double>& out,
    const std::vector<uint8_t>& bc, Workspace* workspace=nullptr) {
    if (n<0 || row.size()!=size_t(n+1) || invdiag.size()!=size_t(n) ||
        diag.size()!=size_t(n) || rhs.size()!=size_t(3*n) ||
        bc.size()!=size_t(3*n) || colors.color_of_node.size()!=size_t(n) ||
        col.size()!=a.size()) throw std::runtime_error("P3: preconditioner dimension mismatch");
    const int nc=colors.count();
    Workspace local_workspace;
    auto& ws=workspace?*workspace:local_workspace;
    ws.y.assign(size_t(3*n),0.0);
    ws.dy.assign(size_t(3*n),0.0);
    auto& y=ws.y;
    auto& dy=ws.dy;
    out.assign(size_t(3*n),0.0);
    // Validate all diagonal slots BEFORE entering a parallel region.
    for(int i=0;i<n;++i)
        if(diag[i]<row[i] || diag[i]>=row[i+1] || col[diag[i]]!=i)
            throw std::runtime_error("P3: missing diagonal block");
    // One OpenMP team per preconditioner application, not per color.
    // Each omp-for has an implicit barrier: all dependencies of color c
    // finish before any worker starts color c+1. Same-colored blocks have
    // no structural couplings, so the result is deterministic.
    #ifdef _OPENMP
    #pragma omp parallel if(n>256)
    #endif
    {
        // (D + L_color)*y = rhs; each block is a projected 3x3 solve.
        for(int color=0;color<nc;++color){
            const int begin=colors.offsets[color],end=colors.offsets[color+1];
            #ifdef _OPENMP
            #pragma omp for schedule(static)
            #endif
            for(int k=begin;k<end;++k){
                const int i=colors.vertices[k],i3=3*i;
                double b[3]={bc[i3]?0.0:rhs[i3],bc[i3+1]?0.0:rhs[i3+1],bc[i3+2]?0.0:rhs[i3+2]};
                for(int pp=row[i];pp<row[i+1];++pp){
                    const int j=col[pp];
                    if(colors.color_of_node[j]>=color)continue;
                    const int j3=3*j;const auto& A=a[pp];
                    for(int r=0;r<3;++r)if(!bc[i3+r])
                        for(int q=0;q<3;++q)b[r]-=A[3*r+q]*y[j3+q];
                }
                for(int r=0;r<3;++r){
                    if(bc[i3+r])continue;
                    for(int q=0;q<3;++q)y[i3+r]+=invdiag[i][3*r+q]*b[q];
                }
                const auto& D=a[diag[i]];
                for(int r=0;r<3;++r)if(!bc[i3+r])
                    for(int q=0;q<3;++q)if(!bc[i3+q])
                        dy[i3+r]+=D[3*r+q]*y[i3+q];
            }
        }
        // (D + U_color)*out = D*y; reverse color sequence is essential
        // for an SPD preconditioner compatible with CG.
        for(int color=nc-1;color>=0;--color){
            const int begin=colors.offsets[color],end=colors.offsets[color+1];
            #ifdef _OPENMP
            #pragma omp for schedule(static)
            #endif
            for(int k=begin;k<end;++k){
                const int i=colors.vertices[k],i3=3*i;
                double b[3]={dy[i3],dy[i3+1],dy[i3+2]};
                for(int pp=row[i];pp<row[i+1];++pp){
                    const int j=col[pp];
                    if(colors.color_of_node[j]<=color)continue;
                    const int j3=3*j;const auto& A=a[pp];
                    for(int r=0;r<3;++r)if(!bc[i3+r])
                        for(int q=0;q<3;++q)b[r]-=A[3*r+q]*out[j3+q];
                }
                for(int r=0;r<3;++r){
                    if(bc[i3+r])continue;
                    for(int q=0;q<3;++q)out[i3+r]+=invdiag[i][3*r+q]*b[q];
                }
            }
        }
    }

}

// P3.1: same symmetric color order and same arithmetic sequence as apply(),
// but traverse only pre-indexed predecessors/successors in original BCSR row order.
// The original implementation is retained as the validation reference.
inline void apply_fast(const Coloring& colors, int n,
    const std::vector<int>& row, const std::vector<int>& col,
    const std::vector<std::array<double,9>>& a,
    const std::vector<std::array<double,9>>& invdiag,
    const std::vector<int>& diag,
    const std::vector<double>& rhs, std::vector<double>& out,
    const std::vector<uint8_t>& bc, Workspace* workspace=nullptr) {
    if (n<0 || row.size()!=size_t(n+1) || invdiag.size()!=size_t(n) ||
        diag.size()!=size_t(n) || rhs.size()!=size_t(3*n) ||
        bc.size()!=size_t(3*n) || colors.color_of_node.size()!=size_t(n) ||
        col.size()!=a.size() || colors.lower_offsets.size()!=size_t(n+1) ||
        colors.upper_offsets.size()!=size_t(n+1)) throw std::runtime_error("P3.1: graph offsets mismatch");
    const int nc=colors.count();
    Workspace local_workspace;
    auto& ws=workspace?*workspace:local_workspace;
    ws.y.assign(size_t(3*n),0.0);
    ws.dy.assign(size_t(3*n),0.0);
    auto& y=ws.y;
    auto& dy=ws.dy;
    out.assign(size_t(3*n),0.0);
    // Validate all diagonal slots BEFORE entering a parallel region.
    for(int i=0;i<n;++i)
        if(diag[i]<row[i] || diag[i]>=row[i+1] || col[diag[i]]!=i)
            throw std::runtime_error("P3: missing diagonal block");
    // One OpenMP team per preconditioner application, not per color.
    // Each omp-for has an implicit barrier: all dependencies of color c
    // finish before any worker starts color c+1. Same-colored blocks have
    // no structural couplings, so the result is deterministic.
    #ifdef _OPENMP
    #pragma omp parallel if(n>256)
    #endif
    {
        // (D + L_color)*y = rhs; each block is a projected 3x3 solve.
        for(int color=0;color<nc;++color){
            const int begin=colors.offsets[color],end=colors.offsets[color+1];
            #ifdef _OPENMP
            #pragma omp for schedule(static)
            #endif
            for(int k=begin;k<end;++k){
                const int i=colors.vertices[k],i3=3*i;
                double b[3]={bc[i3]?0.0:rhs[i3],bc[i3+1]?0.0:rhs[i3+1],bc[i3+2]?0.0:rhs[i3+2]};
                for(int idx=colors.lower_offsets[i];idx<colors.lower_offsets[i+1];++idx){
                    const int pp=colors.lower_positions[idx];
                    const int j=col[pp];
                    const int j3=3*j;const auto& A=a[pp];
                    for(int r=0;r<3;++r)if(!bc[i3+r])
                        for(int q=0;q<3;++q)b[r]-=A[3*r+q]*y[j3+q];
                }
                for(int r=0;r<3;++r){
                    if(bc[i3+r])continue;
                    for(int q=0;q<3;++q)y[i3+r]+=invdiag[i][3*r+q]*b[q];
                }
                const auto& D=a[diag[i]];
                for(int r=0;r<3;++r)if(!bc[i3+r])
                    for(int q=0;q<3;++q)if(!bc[i3+q])
                        dy[i3+r]+=D[3*r+q]*y[i3+q];
            }
        }
        // (D + U_color)*out = D*y; reverse color sequence is essential
        // for an SPD preconditioner compatible with CG.
        for(int color=nc-1;color>=0;--color){
            const int begin=colors.offsets[color],end=colors.offsets[color+1];
            #ifdef _OPENMP
            #pragma omp for schedule(static)
            #endif
            for(int k=begin;k<end;++k){
                const int i=colors.vertices[k],i3=3*i;
                double b[3]={dy[i3],dy[i3+1],dy[i3+2]};
                for(int idx=colors.upper_offsets[i];idx<colors.upper_offsets[i+1];++idx){
                    const int pp=colors.upper_positions[idx];
                    const int j=col[pp];
                    const int j3=3*j;const auto& A=a[pp];
                    for(int r=0;r<3;++r)if(!bc[i3+r])
                        for(int q=0;q<3;++q)b[r]-=A[3*r+q]*out[j3+q];
                }
                for(int r=0;r<3;++r){
                    if(bc[i3+r])continue;
                    for(int q=0;q<3;++q)out[i3+r]+=invdiag[i][3*r+q]*b[q];
                }
            }
        }
    }

}

} // namespace stage3d06::p3

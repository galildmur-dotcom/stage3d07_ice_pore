#pragma once
// Stage3D06-P5. One-level additive Schwarz on nodal 3x3 BCSR graph.
// Two variants: AS0 disjoint cores, AS1 cores plus one complete graph-adjacency layer.
// Each local solve is an SPD zero-fill BLOCK IC(0) approximation, not an exact
// subdomain inverse. The global action sum R_s^T M_s^{-1} R_s remains symmetric
// positive definite on the free-DOF subspace. No partition-of-unity asymmetry.
// Deterministic assembly: independent local solves and a node-owned gather pass.
#include "p4_block_ic0.hpp"
#include <algorithm>
#include <array>
#include <cstdint>
#include <exception>
#include <memory>
#include <numeric>
#include <queue>
#include <stdexcept>
#include <vector>
#ifdef _OPENMP
#include <omp.h>
#endif
namespace stage3d06::p5 {
using B3=std::array<double,9>;
struct LocalPattern {
 std::vector<int> nodes,row,col,source;
};
struct Pattern {
 int n=0,coreSize=0,overlap=0;
 std::vector<LocalPattern> local;
 // Each node is gathered exactly once: list of (subdomain, local node) occurrences.
 std::vector<int> gatherRow, gatherSub, gatherNode;
 std::size_t totalMembers=0;
};
inline Pattern partition(int n,const std::vector<int>&row,const std::vector<int>&col,
                         int coreSize,int overlap){
 if(n<=0||row.size()!=std::size_t(n+1)||row.back()!=int(col.size())||coreSize<1||coreSize>1024||(overlap!=0&&overlap!=1))
  throw std::runtime_error("P5 Schwarz: invalid BCSR graph/partition settings");
 Pattern pat;pat.n=n;pat.coreSize=coreSize;pat.overlap=overlap;
 std::vector<uint8_t> assigned(n,0);
 std::vector<int> visited(n,-1),localIndex(n,-1);int stamp=0;
 for(int seed=0;seed<n;++seed){
  if(assigned[seed])continue;
  // BFS seeded in stable node order. Only unassigned vertices form a disjoint core.
  ++stamp;std::vector<int> queue{seed},core;visited[seed]=stamp;
  std::size_t head=0;
  while(head<queue.size() && int(core.size())<coreSize){
   int i=queue[head++];if(assigned[i])continue;
   assigned[i]=1;core.push_back(i);
   for(int p=row[i];p<row[i+1];++p){int j=col[p];
    if(j<0||j>=n)throw std::runtime_error("P5 Schwarz: invalid adjacency index");
    if(!assigned[j] && visited[j]!=stamp){visited[j]=stamp;queue.push_back(j);}
   }
  }
  // For overlap 1 include ALL graph neighbors of any core vertex, not an arbitrary cap.
  std::vector<int> nodes=core;
  if(overlap)for(int i:core)for(int p=row[i];p<row[i+1];++p)nodes.push_back(col[p]);
  std::sort(nodes.begin(),nodes.end());nodes.erase(std::unique(nodes.begin(),nodes.end()),nodes.end());
  LocalPattern l;l.nodes=std::move(nodes);l.row.assign(l.nodes.size()+1,0);
  for(int j=0;j<int(l.nodes.size());++j)localIndex[l.nodes[j]]=j;
  for(int i=0;i<int(l.nodes.size());++i){int gi=l.nodes[i];
   for(int p=row[gi];p<row[gi+1];++p){int lj=localIndex[col[p]];
    if(lj>=0){l.col.push_back(lj);l.source.push_back(p);}
   }
   l.row[i+1]=int(l.col.size());
  }
  for(int j:l.nodes)localIndex[j]=-1;
  pat.totalMembers+=l.nodes.size();pat.local.push_back(std::move(l));
 }
 pat.gatherRow.assign(n+1,0);
 for(auto&l:pat.local)for(int i:l.nodes)++pat.gatherRow[i+1];
 for(int i=0;i<n;++i)pat.gatherRow[i+1]+=pat.gatherRow[i];
 pat.gatherSub.resize(pat.totalMembers);pat.gatherNode.resize(pat.totalMembers);
 auto cursor=pat.gatherRow;
 for(int s=0;s<int(pat.local.size());++s)
  for(int k=0;k<int(pat.local[s].nodes.size());++k){int i=pat.local[s].nodes[k];int q=cursor[i]++;
   pat.gatherSub[q]=s;pat.gatherNode[q]=k;}
 return pat;
}
struct Local {
 std::vector<B3> blocks;
 std::vector<uint8_t> bc;
 stage3d06::p4::BlockIC0 factor;
 std::vector<double> rhs,sol;
};
struct Schwarz {
 std::shared_ptr<const Pattern> pattern;
 std::vector<Local> local;
 void setup(int n,const std::vector<int>&row,const std::vector<int>&col,
            const std::vector<B3>&blocks,const std::vector<uint8_t>&bc,
            int core,int overlap,std::shared_ptr<const Pattern> reusable={}){
  if(bc.size()!=std::size_t(3*n)||blocks.size()!=col.size())throw std::runtime_error("P5 Schwarz: matrix/BC sizes mismatch");
  if(!reusable)reusable=std::make_shared<const Pattern>(partition(n,row,col,core,overlap));
  if(reusable->n!=n || reusable->coreSize!=core || reusable->overlap!=overlap)
   throw std::runtime_error("P5 Schwarz: cached graph partition incompatible");
  pattern=std::move(reusable);local.clear();local.resize(pattern->local.size());
  // These independent factorizations have no inter-subdomain data dependence.
  // Preserve exceptions instead of letting them escape an OpenMP region.
  std::exception_ptr problem;
  #ifdef _OPENMP
  #pragma omp parallel for schedule(dynamic,1) if(pattern->local.size()>8)
  #endif
  for(int s=0;s<int(local.size());++s){
   try{
    const auto&p=pattern->local[s];auto&z=local[s];
    z.blocks.resize(p.source.size());
    for(std::size_t k=0;k<p.source.size();++k)z.blocks[k]=blocks[p.source[k]];
    z.bc.resize(3*p.nodes.size());
    for(int k=0;k<int(p.nodes.size());++k)for(int c=0;c<3;++c)z.bc[3*k+c]=bc[3*p.nodes[k]+c];
    z.factor.setup(int(p.nodes.size()),p.row,p.col,z.blocks,z.bc);
    z.rhs.resize(z.bc.size());z.sol.resize(z.bc.size());
   }catch(...){
    #ifdef _OPENMP
    #pragma omp critical(p5_errors)
    #endif
    {if(!problem)problem=std::current_exception();}
   }
  }
  if(problem)std::rethrow_exception(problem);
 }
 void apply(const std::vector<double>&v,std::vector<double>&out,const std::vector<uint8_t>&bc){
  if(!pattern||v.size()!=std::size_t(pattern->n*3)||bc.size()!=v.size())throw std::runtime_error("P5 Schwarz: apply dimensions");
  const auto&p=*pattern;
  #ifdef _OPENMP
  #pragma omp parallel for schedule(dynamic,1) if(p.local.size()>8)
  #endif
  for(int s=0;s<int(local.size());++s){
   auto&z=local[s];const auto&nodes=p.local[s].nodes;
   for(int k=0;k<int(nodes.size());++k)for(int c=0;c<3;++c)
    z.rhs[3*k+c]=bc[3*nodes[k]+c]?0.:v[3*nodes[k]+c];
   z.factor.apply(z.rhs,z.sol,z.bc);
  }
  out.assign(v.size(),0.);
  // Each node is owned by exactly one gather iteration: no atomic adds, no races.
  #ifdef _OPENMP
  #pragma omp parallel for schedule(static) if(p.n>1000)
  #endif
  for(int i=0;i<p.n;++i){
   double val[3]={};
   for(int a=p.gatherRow[i];a<p.gatherRow[i+1];++a){const auto&z=local[p.gatherSub[a]];
    int k=p.gatherNode[a];for(int c=0;c<3;++c)val[c]+=z.sol[3*k+c];}
   for(int c=0;c<3;++c)if(!bc[3*i+c])out[3*i+c]=val[c];
  }
 }
};
} // namespace stage3d06::p5

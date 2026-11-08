#pragma once
// Common independent Tet10 curved mesh importer (identical MSH ordering to Stage3D02)
#define STAGE3D01_LIBRARY
#include "geometry_stage3d01.cpp"
#undef STAGE3D01_LIBRARY
struct Imported {Mesh mesh;vector<Face> internal;};
Imported read_msh(const fs::path& file,bool slab=false){
  ifstream f(file);if(!f)throw runtime_error("Cannot read "+file.string());
  Imported a;Mesh&m=a.mesh;m.center={0,0,.03};m.radius=.001;
  unordered_map<int,int> ids;string s;
  while(f>>s){
    if(s=="$MeshFormat"){string ver;int binary,sz;f>>ver>>binary>>sz;if(ver!="2.2"||binary)throw runtime_error("Expected ASCII Gmsh MSH 2.2");}
    else if(s=="$Nodes"){int n;f>>n;m.nodes.resize(n);ids.reserve(2*n);
      for(int i=0;i<n;++i){int id;f>>id>>m.nodes[i].x>>m.nodes[i].y>>m.nodes[i].z;ids.emplace(id,i);}}
    else if(s=="$Elements"){int nel;f>>nel;
      for(int e=0;e<nel;++e){int id,type,nt;f>>id>>type>>nt;vector<int> tags(nt);
        for(int&x:tags)f>>x;if(tags.empty())throw runtime_error("Missing physical tag");
        if(type==11){if(tags[0]!=1)throw runtime_error("Non-ice Tet10");Tet t;
          for(int&v:t){int idn;f>>idn;v=ids.at(idn);}swap(t[8],t[9]);m.tets.push_back(t);}
        else if(type==9){Face q;q.tag=tags[0];for(int&v:q.nodes){int idn;f>>idn;v=ids.at(idn);}if(q.tag==9)a.internal.push_back(q);else m.faces.push_back(q);}
        else throw runtime_error("Unexpected Gmsh element type "+to_string(type));
      }}
  }
  if(m.nodes.empty()||m.tets.empty()||m.faces.empty()||(!slab&&a.internal.empty()))throw runtime_error("Incomplete mesh or absent B6 interface");
  array<int,10> ct{};for(auto&face:m.faces){if(face.tag<2||face.tag>8)throw runtime_error("Unknown thermal face tag");ct[face.tag]++;}for(int j=2;j<=(slab?7:8);++j)if(!ct[j])throw runtime_error("Missing surface tag");
  return a;
}

array<double,6> triN(double r,double s){double L[]={1-r-s,r,s};array<double,6>N;
  for(int i=0;i<3;++i)N[i]=L[i]*(2*L[i]-1);
  N[3]=4*L[0]*L[1];N[4]=4*L[1]*L[2];N[5]=4*L[2]*L[0];return N;
}

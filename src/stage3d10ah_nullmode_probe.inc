// Stage3D10AH: near-rigid vertical-translation mode, step-6 diagnostic only.
// Included by P10AG; does not solve a linear system or alter the mechanics.
namespace p10ah {
struct Measure {
 std::size_t free_z=0,pinned_z=0;
 std::size_t pinned_node=0;
 double rayleigh=0,rayleigh_from_pin=0,pin_identity_rel=0;
 double kmode_norm=0,rhs_projection=0,rhs_mode_cosine=0;
 double rhs_z_sum=0,probe_rayleigh=0,rayleigh_contrast=0;
};

Measure inspect(const BCSR& K,const std::vector<uint8_t>& bc,
                const std::vector<double>& rhs,double probe_rayleigh,
                const ice3d::p10e::ReverseGraph* graph=nullptr){
 const std::size_t ndof=std::size_t(K.n)*3;
 if(bc.size()!=ndof||rhs.size()!=ndof)
  throw std::runtime_error("P10AH: inconsistent BCSR/BC/RHS dimensions");
 Measure m;
 m.probe_rayleigh=probe_rayleigh;
 for(int i=0;i<K.n;++i){
  if(bc[3*std::size_t(i)+2]){++m.pinned_z;m.pinned_node=std::size_t(i);}
  else ++m.free_z;
 }
 if(m.pinned_z!=1||m.free_z<1)
  throw std::runtime_error("P10AH: expected exactly one vertical gauge pin");
 const double amplitude=1./std::sqrt(double(m.free_z));
 std::vector<double> z(ndof,0.);
 for(int i=0;i<K.n;++i)if(!bc[3*std::size_t(i)+2])
  z[3*std::size_t(i)+2]=amplitude;
 std::vector<double> Kz;
 ice3d::p10e::multiply(K,z,Kz,bc,true,graph);
 long double e=0.,b=0.,sum_z=0.;
 for(std::size_t i=0;i<ndof;++i){
  e+=(long double)z[i]*(long double)Kz[i];
  b+=(long double)z[i]*(long double)rhs[i];
  if(i%3==2&&!bc[i])sum_z+=(long double)rhs[i];
 }
 m.rayleigh=double(e);
 m.kmode_norm=ice3d::p10e::norm(Kz);
 m.rhs_projection=double(b);
 m.rhs_z_sum=double(sum_z);
 const double bnorm=ice3d::p10e::norm(rhs);
 m.rhs_mode_cosine=bnorm?m.rhs_projection/bnorm:0.;
 const int pin=int(m.pinned_node);
 const auto& r=K.rows();const auto& c=K.cols();
 const auto lo=c.begin()+r[pin],hi=c.begin()+r[pin+1];
 const auto it=std::lower_bound(lo,hi,pin);
 if(it==hi||*it!=pin)throw std::runtime_error("P10AH: missing pin diagonal block");
 const double pin_kzz=K.a[std::size_t(it-c.begin())][8];
 m.rayleigh_from_pin=pin_kzz/double(m.free_z);
 m.pin_identity_rel=std::abs(m.rayleigh-m.rayleigh_from_pin)/
    std::max({1e-300,std::abs(m.rayleigh),std::abs(m.rayleigh_from_pin)});
 m.rayleigh_contrast=m.rayleigh>0.?probe_rayleigh/m.rayleigh:0.;
 return m;
}

void save(const std::filesystem::path& path,const std::string& mesh,
          const Measure& m){
 std::ofstream f(path);
 if(!f)throw std::runtime_error("P10AH: cannot create diagnostic CSV");
 f<<"mesh,step,functional,free_z_dofs,pinned_z_dofs,pin_node,"
   "vertical_mode_rayleigh,expected_rayleigh_from_single_pin,"
   "pin_identity_relative_difference,vertical_mode_operator_norm,"
   "rhs_projection_on_unit_vertical_mode,rhs_mode_cosine,"
   "sum_free_rhs_z,random_probe_min_rayleigh,"
   "probe_to_vertical_rayleigh_contrast\n";
 f<<std::setprecision(17)<<mesh<<",6,jen,"<<m.free_z<<','<<m.pinned_z
  <<','<<m.pinned_node<<','<<m.rayleigh<<','<<m.rayleigh_from_pin
  <<','<<m.pin_identity_rel<<','<<m.kmode_norm<<','<<m.rhs_projection
  <<','<<m.rhs_mode_cosine<<','<<m.rhs_z_sum<<','<<m.probe_rayleigh
  <<','<<m.rayleigh_contrast<<'\n';
 f.close();if(!f)throw std::runtime_error("P10AH: incomplete diagnostic CSV");
}

void report(const Measure& m){
 std::cout<<std::scientific<<std::setprecision(11)
  <<"P10AH_NULLMODE_RESULT free_z="<<m.free_z
  <<" pinned_z="<<m.pinned_z
  <<" rayleigh_z="<<m.rayleigh
  <<" expected_from_pin="<<m.rayleigh_from_pin
  <<" pin_identity_rel="<<m.pin_identity_rel
  <<" rhs_mode_cosine="<<m.rhs_mode_cosine
  <<" rhs_sum_z="<<m.rhs_z_sum
  <<" rayleigh_contrast="<<m.rayleigh_contrast
  <<"\nP10AH_NULLMODE_DIAGNOSTIC_OK\n"<<std::flush;
}

void selftest(){
 // Exact one-dimensional vertical 2-node spring with one pinned z DOF.
 BCSR K;K.n=2;K.row={0,2,4};K.col={0,1,0,1};
 K.a.resize(4);
 K.a[0]={1.,0.,0.,0.,1.,0.,0.,0.,2.};
 K.a[1]={0.,0.,0.,0.,0.,0.,0.,0.,-2.};
 K.a[2]=K.a[1];
 K.a[3]=K.a[0];
 std::vector<uint8_t> bc(6,0);bc[2]=1;
 std::vector<double> rhs(6,0.);rhs[5]=3.;
 const auto m=inspect(K,bc,rhs,4.);
 if(m.free_z!=1||m.pinned_z!=1||std::abs(m.rayleigh-2.)>1e-13||
    std::abs(m.pin_identity_rel)>1e-13||std::abs(m.rhs_mode_cosine-1.)>1e-13||
    std::abs(m.rayleigh_contrast-2.)>1e-13)
  throw std::runtime_error("P10AH: selftest pinned vertical mode mismatch");
 std::cout<<"P10AH_SELFTEST_OK vertical_mode=1 pin_identity=1 rhs_projection=1\n";
}
} // namespace p10ah

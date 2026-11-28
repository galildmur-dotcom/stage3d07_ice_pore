#include <cmath>
#include <iomanip>
#include <iostream>
#include <vector>
#include "lapacke.h"
int main(){
 const double pi=3.141592653589793238462643383279502884;
 for(int P=2;P<=8;++P){
  std::vector<double> a(P*P),U(P*P),Vt(P*P),s(P),superb(P);
  for(int i=0;i<P;++i){
   double t=.5-.5*std::cos(pi*i/(P-1));
   for(int j=0;j<P;++j){
    double binom=1;
    for(int k=1;k<=j;++k)binom*=(P-k)/double(k);
    a[i*P+j]=binom*std::pow(t,j)*std::pow(1-t,P-1-j);
   }
  }
  int info=LAPACKE_dgesvd(LAPACK_ROW_MAJOR,'A','A',P,P,a.data(),P,
                         s.data(),U.data(),P,Vt.data(),P,superb.data());
  std::cout<<"P10PW_LAPACKE_SVD P="<<P<<" info="<<info
           <<" s_first="<<s.front()<<" s_last="<<s.back()<<std::endl;
  if(info!=0)return 2;
 }
}

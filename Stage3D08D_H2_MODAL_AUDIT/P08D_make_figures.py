#!/usr/bin/env python3
# Optional plotting helper: requires matplotlib+numpy, numerical source is the
# independent standard-library P08D_modal_surface.py reconstruction.
import sys,csv,math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import cm,colors
sys.path.insert(0,str(Path(__file__).resolve().parent))
from P08D_modal_surface import read_coefficients,gradient,R_PORE,C
p=Path('/mnt/data')
d0,_=read_coefficients(p/'P08D_SENSITIVITIES.csv')
d2,_=read_coefficients(p/'P08D_SENSITIVITIES(1).csv')
out=p/'P08D_MODAL_H2'
ths=np.linspace(0,180,1001)
mu=np.cos(np.deg2rad(ths))
fig,axs=plt.subplots(2,1,figsize=(9.0,7.0),sharex=True,layout='constrained')
for ax,key,title,scale,unit in [
 (axs[0],'D_mean_per_m','(a) Среднее значение функционала',1,'м⁻³'),
 (axs[1],'D_variance_per_m','(б) Дисперсия функционала',1,'м⁻³')]:
 ax.plot(ths,[gradient(m,d2[key]) for m in mu],label='H2 (основной результат)',linewidth=2.3)
 ax.plot(ths,[gradient(m,d0[key]) for m in mu],label='H0 (контроль)',linestyle='--',linewidth=1.4)
 ax.axhline(0,color='grey',linewidth=.75)
 ax.set_title(title,loc='left')
 ax.set_ylabel('Проекция g, '+unit)
 ax.grid(True,alpha=.20)
 ax.legend(fontsize=9)
axs[-1].set_xlabel('Полярный угол θ от оси +z, градусы')
axs[-1].set_xticks(np.arange(0,181,30))
fig.suptitle('Низкомодовая реконструкция чувствительности поверхности поры\nR + tz + Y₂₀; Δt = 300 с; t_f = 3600 с; GH3',fontsize=13)
fig.savefig(out/'P08D_MODAL_MERIDIAN_H0_H2.png',dpi=180)
plt.close(fig)

# 3D representation of the same axisymmetric modal projection, not new FEM data.
theta=np.linspace(0,np.pi,72)
phi=np.linspace(0,2*np.pi,145)
th,ph=np.meshgrid(theta,phi,indexing='ij')
xx=np.sin(th)*np.cos(ph)
yy=np.sin(th)*np.sin(ph)
zz=np.cos(th)
fig=plt.figure(figsize=(11,5.7),layout='constrained')
for num,(key,title) in enumerate([('D_mean_per_m','(a) Ожидание'),('D_variance_per_m','(б) Дисперсия')],start=1):
 ax=fig.add_subplot(1,2,num,projection='3d')
 dat=np.array([[gradient(float(m),d2[key]) for m in row] for row in zz])
 vmax=float(np.max(np.abs(dat)))
 norm=colors.TwoSlopeNorm(vmin=-vmax,vcenter=0,vmax=vmax)
 surf=ax.plot_surface(xx,yy,zz,rstride=1,cstride=1,facecolors=cm.coolwarm(norm(dat)),linewidth=0,antialiased=False,shade=False)
 ax.view_init(elev=22,azim=-55)
 ax.set_box_aspect((1,1,1))
 ax.set_axis_off()
 ax.set_title(title+' — H2',fontsize=12)
 sm=cm.ScalarMappable(norm=norm,cmap=cm.coolwarm)
 sm.set_array(dat)
 cb=fig.colorbar(sm,ax=ax,shrink=.63,pad=.01,aspect=25)
 cb.set_label('g, м⁻³')
fig.suptitle('Осесимметричная L²-проекция градиента формы по трём модам\nПредварительная визуализация, не точечная сопряжённая чувствительность',fontsize=12)
fig.savefig(out/'P08D_MODAL_SPHERE_H2.png',dpi=180)
plt.close(fig)
print('Figures made')

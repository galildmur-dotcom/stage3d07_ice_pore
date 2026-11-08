# Воспроизведение геометрии H3/H4 (необязательно для запуска FEM)

Источник — Gmsh 4.15.2, OpenCASCADE, исходная геометрия `sphere_pore_B6_refined.geo`, MSH 2.2 ASCII, Tet10.

Размеры в метрах: `nearSize(H3)=0.000190`, `nearSize(H4)=0.000135`, `farSize=0.003900`. Эти параметры управляют размером сетки, а не непосредственно длинами рёбер каждого элемента. Во время генерации для воспроизводимости используется `-nt 2` и одинаковые параметры Gmsh, но на разных ОС/версиях Gmsh сетки не обязаны быть побитово идентичными.

```sh
gmsh sphere_pore_B6_refined.geo -3 -nt 2 -format msh2 -setnumber nearSize 0.00019 -setnumber farSize 0.0039 -o H3.msh
gmsh sphere_pore_B6_refined.geo -3 -nt 2 -format msh2 -setnumber nearSize 0.000135 -setnumber farSize 0.0039 -o H4.msh
```

В поставке уже включены обе готовые сетки и результаты проверки геометрии, Gmsh пользователю для запуска не нужен.

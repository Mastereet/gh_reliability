# 基于已知内外径圆环靶标的多视图联合 Gauss–Helmert 圆重建与不确定度传播：从 GH(2014) 单圆模型到同心双圆模型的纯理论闭环改造

## 摘要

本文以 Soheilian 与 Brédif 在 *Multi-view 3D Circular Target Reconstruction with Uncertainty Analysis*（下文简称 GH, 2014）中的单圆多视图 Gauss–Helmert（GH）重建框架为理论母体，讨论如何把“已知内外径的同心圆环靶标”严格改造为“双圆联合”的纯理论闭环系统。目标是：在每幅图像中，从内外两条边界分别输出双对偶二次曲线
\(\operatorname{vec5}(E^*)\) 及其协方差；随后将两条边界与相机位姿不确定度共同纳入多视图联合 GH 求解；最后回答“是否有望比 GH(2014) 的单圆方案得到更高精度”。

全文坚持两条原则。第一，所有核心投影、对偶化、GH 线性化和同心圆透视几何公式均来自已有文献，而不是随意臆造。第二，凡是不得不做的工程近似，都与“纯理论主链”明确分离。本文的主结论是：**在内外两条边界都能被无偏、稳定地提取，且相机网络几何、畸变建模和权矩阵设定合理的前提下，已知内外径的同心圆环靶标，理论上可以比 GH(2014) 的单圆模型取得更高精度；但该提升不是无条件的，尤其会受到反光内圆带来的系统偏差和镜头畸变未建模误差的限制。**

---

## 1. 引言

GH(2014) 给出了一个非常完整的单圆闭环：

1. 在每一幅图像中，用 GH 模型拟合二维椭圆，并把 2D 轮廓点的不确定度传播到椭圆参数协方差；
2. 把这些带协方差的二维椭圆以及带协方差的相机位姿一并作为观测；
3. 用 3D 圆的最小参数化和非线性 Gauss–Helmert 模型，联合估计 3D 圆参数与相机位姿改正，并输出协方差。

你的目标与 GH(2014) 的差别在于：图像中的目标不是单圆，而是“黑色圆环 + 中间反光内圆”的**同心双圆边界**。如果将外边界和内边界都视为物理圆，那么在透视投影下，它们分别变成两条椭圆，且满足：

- 它们来自同一平面；
- 它们 3D 中心相同；
- 它们法向一致；
- 它们半径 \(\rho_{\text{out}},\rho_{\text{in}}\) 已知。

因此，相比单圆，圆环靶标天然多出两类信息：

- **额外观测信息**：每视图从 1 条椭圆增加到 2 条椭圆；
- **额外几何先验**：已知内外径、同心、共面。

这些信息都可以在不破坏 GH(2014) 投影理论的前提下，被直接吸收到一个“双分支联合 GH”模型中。

---

## 2. 相关工作

### 2.1 单椭圆拟合与不确定度传播

- **Fitzgibbon, Pilu, Fisher (1999)**：给出了经典的直接最小二乘椭圆拟合方法。其标准点二次曲线写法为
  \[
  ax^2+bxy+cy^2+dx+ey+f=0,
  \]
  通过约束 \(4ac-b^2=1\) 把“仅保留椭圆”这一条件嵌入广义特征值问题中。该方法非常适合作为初始化。
- **GH(2014)**：采用另一种系数写法
  \[
  ax^2+2bxy+cy^2+2dx+2ey+f=0,
  \]
  对应的椭圆约束变为
  \[
  ac-b^2=1.
  \]
  GH 的关键贡献不只是拟合椭圆，而是把 2D 轮廓点协方差传播到对偶椭圆 \(E^*\) 的 \(\operatorname{vec5}(E^*)\) 协方差上。

### 2.2 单圆/椭圆的多视图三维重建

- **Quan (1996)**：双视图圆锥曲线重建与对应；
- **Mai, Hung, Chesi (2010)**：多视图三维椭圆估计；
- **Bergamasco et al. (2012)**：多相机 3D 椭圆拟合；
- **GH(2014)**：把“3D 圆而非 3D 椭圆”作为直接未知量，并联合位姿不确定度。

### 2.3 同心圆的投影几何

- **Jiang & Quan (ICCV 2005)**：指出同心圆对在标定里比点特征更“几何丰富”，并用构造法逼近投影圆心；
- **Huang, Zhang, Cheung (CVPR 2015)**：研究同心圆的 common self-polar triangle，证明其公共顶点与对边所在直线分别编码了圆心和支撑平面的无穷远线；
- **Calvet et al. (CVPR 2016, CCTag)**：利用同心黑环的投影几何，在挑战性成像条件下高精度定位“公共圆心的图像”；
- **Wang, Chern, Alexa (2019)**：给出基于两条投影椭圆恢复“透视意义下真实圆心图像”和半径比的特征值方法；
- **Hao et al. (Scientific Reports 2021)**：证明投影后的两个椭圆中心与真实投影圆心共线，并给出基于切线/几何约束的高精度提取方法；
- **Huo et al. (Applied Sciences 2024)**：把同心圆中心定位与迭代相机补偿结合，用于提高标定精度。

### 2.4 开源实现生态

- **OpenCV**：提供 `fitEllipse`, `fitEllipseAMS`, `fitEllipseDirect`，适合做椭圆初始化，但不直接提供 GH 协方差传播；
- **CCTag**：提供同心环标记检测与公共圆心定位，是很强的前端；
- **RUNE-Tag**：也是基于圆形高对比特征/同心层布局的 fiducial 系统；
- **Danaozhong/3D-Circle-Reconstruction-from-2D-Ellipses**：给出单圆从多视图椭圆重建的公开示例，但不覆盖“同心双圆 + 不确定度 GH”的完整链条。

---

## 3. 符号、几何对象与目标输出

### 3.1 2D 圆锥曲线及其对偶

GH(2014) 采用如下二维点二次曲线：

\[
ax^2+2bxy+cy^2+2dx+2ey+f=0.
\]

齐次形式为

\[
\begin{bmatrix}x&y&1\end{bmatrix}
E
\begin{bmatrix}x\\y\\1\end{bmatrix}=0,
\qquad
E=
\begin{bmatrix}
a & b & d\\
b & c & e\\
d & e & f
\end{bmatrix}.
\]

对偶二次曲线记为 \(E^*\)。对于满秩椭圆，有

\[
E^*=E^{-1}=\frac{\operatorname{comatrix}(E)^T}{\det(E)}\sim \operatorname{comatrix}(E).
\]

编码方式采用 GH(2014) 的

\[
\operatorname{vec6}(M)=
(M_{11},M_{12},M_{22},M_{13},M_{23},M_{33})^T,
\]
\[
\operatorname{vec5}(M)=
(M_{11},M_{12},M_{22},M_{13},M_{23})^T.
\]

由于 GH 把对偶椭圆归一到 \(E^*_{33}=1\)，因此每个椭圆最终只需输出 \(\operatorname{vec5}(E^*)\)。

### 3.2 每视图需要输出的量

对第 \(j\) 幅图像，分别对外圆和内圆输出

\[
y_{j,\text{out}}=
\Big(\operatorname{vec5}(E^**{j,\text{out}}),\;\Sigma*{j,\text{out}}\Big),
\]
\[
y_{j,\text{in}}=
\Big(\operatorname{vec5}(E^**{j,\text{in}}),\;\Sigma*{j,\text{in}}\Big).
\]

其中

- \(E^*_{j,\text{out}}\)：外边界椭圆的对偶二次曲线；
- \(E^*_{j,\text{in}}\)：内边界椭圆的对偶二次曲线；
- \(\Sigma_{j,\text{out}},\Sigma_{j,\text{in}}\)：对应 \(\operatorname{vec5}\) 的协方差矩阵。

这正是进入多视图 GH 后端的最自然数据形式。

---

## 4. 单视图前端：从轮廓点到 \(\operatorname{vec5}(E^*)\) 与协方差

本节完全沿用 GH(2014) 的理论，只是对“外边界”和“内边界”各执行一次。

### 4.1 GH(2014) 的二维椭圆 GH 拟合

对某条边界的轮廓点，设观测为

\[
l=(x_1,y_1,\ldots,x_n,y_n)^T,
\]

未知椭圆参数为

\[
x=(a,b,c,d,e,f)^T.
\]

GH(2014) 采用如下约束系统：

\[
f(x,l)=ax^2+2bxy+cy^2+2dx+2ey+f=0,
\]
\[
f_c(x)=ac-b^2-1=0.
\]

线性化后得到

\[
A\delta+Br+w=0,
\]
\[
D\delta+w_c=0,
\]
其中

\[
A=\frac{\partial f}{\partial x},\qquad
B=\frac{\partial f}{\partial l},\qquad
D=\frac{\partial f_c}{\partial x}.
\]

对应变分函数为

\[
\Phi=r^TC_r^{-1}r+2k^T(A\delta+Br+w)+2k_c^T(D\delta+w_c).
\]

GH(2014) 给出的法方程写成

\[
\begin{bmatrix}
N & D^T\\
D & 0
\end{bmatrix}
\begin{bmatrix}
\hat\delta\\
\hat k_c
\end{bmatrix}+
\begin{bmatrix}
u\\w_c
\end{bmatrix}=
\begin{bmatrix}0\\0\end{bmatrix},
\]

其中

\[
u=A^TMw,
\qquad
N=A^TMA,
\qquad
M=(BC_rB^T)^{-1}.
\]

观测改正为

\[
\hat r=-C_rB^TM(A\hat\delta+w).
\]

参数协方差由逆法方程读出：

\[
\begin{bmatrix}
C_{\hat\delta} & S^T\\
S & T
\end{bmatrix}=
\begin{bmatrix}
N & D^T\\
D & 0
\end{bmatrix}^{-1}.
\]

### 4.2 点集归一化

为改善数值稳定性，GH(2014) 先将点集用仿射矩阵

\[
M_{\text{den}}=
\begin{bmatrix}
s_x & 0 & m_x\\
0 & s_y & m_y\\
0 & 0 & 1
\end{bmatrix}
\]

进行归一化/反归一化。对归一化后的椭圆

\[
\operatorname{vec6}(E_0)=(a,b,c,d,e,f)^T,
\qquad ac-b^2=1.
\]

### 4.3 对偶化

由 GH(2014) 的式(14)–(18)，归一化椭圆的对偶可写成

\[
E_0^*=
\begin{bmatrix}
cf-e^2 & de-bf & be-cd\\
de-bf & af-d^2 & bd-ae\\
be-cd & bd-ae & 1
\end{bmatrix},
\]

于是

\[
\operatorname{vec5}(E_0^*)=
(cf-e^2,\;de-bf,\;af-d^2,\;be-cd,\;bd-ae)^T.
\]

协方差的一阶传播为

\[
\Sigma_{\operatorname{vec5}(E_0^*)}
=J_{\text{dual}}\,\Sigma_{\operatorname{vec6}(E_0)}\,J_{\text{dual}}^T,
\]

其中显式雅可比为

\[
J_{\text{dual}}=
\begin{bmatrix}
0 & 0 & f & 0 & -2e & c\\
0 & -f & 0 & e & d & -b\\
f & 0 & 0 & -2d & 0 & a\\
0 & e & -d & -c & b & 0\\
-e & d & 0 & b & -a & 0
\end{bmatrix}.
\]

### 4.4 对偶椭圆的反归一化

GH(2014) 使用

\[
E^*=M_{\text{den}}E_0^*M_{\text{den}}^T,
\]

从而

\[
\operatorname{vec5}(E^*)=J_{\text{den}}\operatorname{vec5}(E_0^*)+
\begin{bmatrix}
m_x^2\\m_xm_y\\m_y^2\\m_x\\m_y
\end{bmatrix},
\]

\[
\Sigma_{\operatorname{vec5}(E^*)}
=J_{\text{den}}\Sigma_{\operatorname{vec5}(E_0^*)}J_{\text{den}}^T,
\]

其中

\[
J_{\text{den}}=
\begin{bmatrix}
s_x^2 & 0 & 0 & 2s_xm_x & 0\\
0 & s_xs_y & 0 & s_xm_y & s_ym_x\\
0 & 0 & s_y^2 & 0 & 2s_ym_y\\
0 & 0 & 0 & s_x & 0\\
0 & 0 & 0 & 0 & s_y
\end{bmatrix}.
\]

### 4.5 本问题中的单视图输出

对圆环的外边界和内边界，分别执行 4.1–4.4，即可得到：

\[
\big(\operatorname{vec5}(E^**{j,\text{out}}),\Sigma*{j,\text{out}}\big),
\qquad
\big(\operatorname{vec5}(E^**{j,\text{in}}),\Sigma*{j,\text{in}}\big).
\]

这一步不需要改变 GH(2014) 的任何公式。

### 4.6 工程近似：Fitzgibbon / OpenCV 作为初始化

工程上通常先用 Fitzgibbon (1999) 或 OpenCV 的 `fitEllipseDirect` / `fitEllipseAMS` 得到高质量初值，再进入 GH 椭圆拟合与协方差传播。这里要注意两个“表示差异”：

1. Fitzgibbon 的标准写法是 \(ax^2+bxy+cy^2+dx+ey+f=0\)，约束是 \(4ac-b^2=1\)；
2. GH 的写法是 \(ax^2+2bxy+cy^2+2dx+2ey+f=0\)，约束是 \(ac-b^2=1\)。

因此，如果前端用了 OpenCV/Fitzgibbon，进入 GH 后端前必须把参数表示统一。

---

## 5. 同心双圆在单视图中的附加投影几何：用于一致性检查与更稳初始化

GH(2014) 的单圆框架并不利用“同心双圆”的特殊性质。你的圆环恰好可以引入这一额外理论层。

### 5.1 两条椭圆可以恢复真实投影圆心，而不是误用椭圆中心

仅凭单个椭圆，通常不能恢复“原始圆心在图像中的透视投影”；椭圆的几何中心一般**不是**真实投影圆心。同心双圆改变了这一点。

### 5.2 Wang–Chern–Alexa (2019) 的特征值方法

设两条投影椭圆的**点二次曲线矩阵**为 \(Q_1,Q_2\)（若已知的是对偶椭圆，则先取逆得到点二次曲线）。定义

\[
A:=Q_2Q_1^{-1}.
\]

该文证明，对同心圆的任意透视像，求解

\[
\det(-\lambda Q_1+Q_2)=0
\]

等价于求解矩阵 \(A\) 的特征值问题。若 \((\lambda_i,u_i)\) 为特征对，且 \(\lambda_1\approx\lambda_2\) 为重复特征值、\(\lambda_3\) 为区分特征值，则真实投影圆心可由

\[
\tilde p = Q_1^{-1}u_3,
\qquad
p=(\tilde p_x/\tilde p_z,\tilde p_y/\tilde p_z)
\]

得到；半径比满足

\[
\lambda_1:\lambda_2:\lambda_3=1:1:R^2/r^2,
\]

并可在噪声下用文中给出的对称化公式估计：

\[
\frac{R}{r}\approx
\sqrt{\frac{\lambda_2\lambda_3}{\lambda_1^2}}
\approx
\sqrt{\frac{\lambda_1\lambda_3}{\lambda_2^2}}
\approx
\sqrt{\frac{\lambda_3^2}{\lambda_1\lambda_2}}.
\]

**对本问题的意义**：

- 你的靶标内外径已知，所以理论半径比已知；
- 因而每个视图都可以做一个“投影半径比一致性检查”；
- 同时还可得到一个“真实投影圆心”的高质量初值，而不是用椭圆中心代替。

### 5.3 Huang–Zhang–Cheung (CVPR 2015) 的 common self-polar triangle

该文证明：对同心圆的两条投影椭圆，存在无穷多个 common self-polar triangles，并且它们满足两个关键性质：

1. 所有三角形共享一个公共顶点；
2. 该顶点的对边都落在同一条直线上，该直线对应支撑平面的无穷远线；
3. 这些三角形都是直角三角形。

于是，两条椭圆不仅编码了“圆心的图像”，还编码了“支撑平面的无穷远线”。这对于理解同心圆为何比单圆携带更多的单视图几何信息非常关键。

### 5.4 Hao et al. (2021) 的“椭圆中心共线”结果

对点二次曲线

\[
Q=
\begin{bmatrix}
a & b/2 & d/2\\
b/2 & c & e/2\\
d/2 & e/2 & f
\end{bmatrix},
\]

其椭圆中心为

\[
x_{ec}=\frac{2cd-be}{b^2-4ac},
\qquad
y_{ec}=\frac{2ae-bd}{b^2-4ac}.
\]

进一步，若世界中的圆半径为 \(r\)，则文中给出

\[
x_{ec}=\frac{C+r^2D}{A+r^2B},
\qquad
y_{ec}=\frac{E+r^2F}{A+r^2B},
\]

其中 \(A,B,C,D,E,F\) 仅与单应矩阵有关。对于两条同心圆，文中推得连接两个椭圆中心的直线斜率为

\[
k=\frac{BE-AF}{BC-AD},
\]

与半径无关，因此**两个投影椭圆中心与真实投影圆心共线**。

**对本问题的意义**：

- 它为每幅图像提供了一个极便宜的几何一致性检验；
- 可用于粗剔除错误边界配对；
- 也可作为 GH 联合优化之前的初始化与质量门控。

---

## 6. 多视图理论后端：从 GH(2014) 单圆到“已知内外径同心双圆”的联合 GH

这一节是全文核心。关键思想不是重新发明投影公式，而是：**把 GH(2014) 的单圆投影方程复制成内圆、外圆两条分支，并利用“已知半径 + 同心 + 共面”把两条分支耦合成共享未知量的联合模型。**

### 6.1 GH(2014) 的 3D 圆对偶二次曲面

GH(2014) 证明，一个 3D 圆可由中心 \(C\in\mathbb R^3\) 和半径缩放法向量 \(N\in\mathbb R^3\) 表示，其中

\[
\rho^2=\|N\|^2,
\]

其对偶二次曲面为

\[
Q^*=
\begin{bmatrix}
CC^T+NN^T-\|N\|^2I_3 & C\\
C^T & 1
\end{bmatrix}.
\]

GH 还给出等价写法

\[
Q^*=
\begin{bmatrix}
[N]_\times^2 & 0\\
0 & 0
\end{bmatrix}
+
\begin{bmatrix}C\\1\end{bmatrix}
\begin{bmatrix}C\\1\end{bmatrix}^T.
\]

### 6.2 单圆的透视投影（GH 原式）

若相机投影写成

\[
P=KR\,[I_3\; -S],
\qquad M:=KR,
\]

则 GH(2014) 的单圆投影对偶二次曲线为

\[
E^*=M\Big((C-S)(C-S)^T+[N]_\times^2\Big)M^T.
\]

逐元素形式为

\[
E^*_{ij}=((C-S)\cdot M_i)((C-S)\cdot M_j)
-(N\times M_i)\cdot(N\times M_j).
\]

### 6.3 已知内外径同心双圆的直接 specialization

现在令

- 外圆半径为 \(\rho_{\text{out}}\)；
- 内圆半径为 \(\rho_{\text{in}}\)；
- 两个圆共享同一 3D 中心 \(C\)；
- 两个圆共享同一支撑平面法向方向 \(n\)，且 \(\|n\|=1\)。

由于 GH(2014) 中 \(N\) 本来就定义为“半径缩放后的法向量”，因此对第 \(k\in\{\text{out},\text{in}\}\) 个圆，直接令

\[
N_k=\rho_k n,
\qquad \rho_k\in\{\rho_{\text{out}},\rho_{\text{in}}\}.
\]

这不是新投影理论，只是 GH 定义 \(N=\rho W\) 的直接改写。于是每个视图 \(j\) 上，两条分支都满足 GH 的原始投影式：

\[
E^**{j,k}=M_j\Big((C-S_j)(C-S_j)^T+[\rho_k n]*\times^2\Big)M_j^T,
\qquad k\in\{\text{out},\text{in}\}.
\]

### 6.4 每视图的观测方程

GH(2014) 对单条椭圆使用如下 5 维方程：

\[
F(E^*,E^**{\text{obs}})=
\operatorname{vec5}(E^*)-E^**{33}\operatorname{vec5}(E^*_{\text{obs}})=0.
\]

因此对圆环的每个视图 \(j\)，自然得到两条观测方程：

\[
F_{j,\text{out}}(X,L_j)=
\operatorname{vec5}(E^*_{j,\text{out}})-E^**{j,\text{out},33}\operatorname{vec5}(E^**{j,\text{out,obs}})=0,
\]

\[
F_{j,\text{in}}(X,L_j)=
\operatorname{vec5}(E^*_{j,\text{in}})-E^**{j,\text{in},33}\operatorname{vec5}(E^**{j,\text{in,obs}})=0.
\]

把全部视图堆叠后，整体系统就是

\[
F(X,L)=
\begin{bmatrix}
F_{1,\text{out}}\\
F_{1,\text{in}}\\
\vdots\\
F_{m,\text{out}}\\
F_{m,\text{in}}
\end{bmatrix}=0.
\]

### 6.5 观测向量与未知向量

与 GH(2014) 一样，每个视图都可以把相机位姿也当作带协方差的观测。于是对第 \(j\) 幅图像，可取观测向量

\[
L_j=
\big(
\text{pose}*j,
\operatorname{vec5}(E^**{j,\text{out,obs}}),
\operatorname{vec5}(E^*_{j,\text{in,obs}})
\big).
\]

若继续沿用 GH 的“位姿不确定、内参固定”的设定，则

- \(\text{pose}_j\) 可由投影中心 \(S_j\) 与旋转参数（或等价的 \(M_j=K R_j\)）表示；
- \(\Sigma_{\text{pose},j}\) 为位姿协方差；
- \(\Sigma_{j,\text{out}},\Sigma_{j,\text{in}}\) 为两条椭圆的对偶协方差。

未知量可以取为

\[
X=(C,n),
\]

也可以采用更贴近 GH 的参数化：取外圆的半径缩放法向量 \(N_{\text{out}}\) 为未知，再通过已知半径比构造内圆

\[
N_{\text{in}}=\frac{\rho_{\text{in}}}{\rho_{\text{out}}}N_{\text{out}},
\]

并附加已知半径约束

\[
N_{\text{out}}^TN_{\text{out}}-\rho_{\text{out}}^2=0.
\]

这两种写法本质等价：前者把“单位法向”显式化，后者更接近 GH 的原始变量定义。

### 6.6 Jacobian：仍然是 GH(2014) 的 Jacobian，只做代入/链式法则

GH(2014) 给出单圆残差的关键导数：

\[
\frac{\partial F}{\partial\operatorname{vec5}(E^*_{\text{obs}})}=-E^*_{33}I_5,
\]

\[
\frac{\partial F}{\partial\operatorname{vec6}(E^*)}=
\big[I_5\; -\operatorname{vec5}(E^*_{\text{obs}})\big],
\]

\[
\frac{\partial \operatorname{vec6}(E^*)}{\partial M_{ij}}=
\operatorname{vec6}(\delta_i\Gamma_j^T+\Gamma_j\delta_i^T),
\]

其中

\[
\Gamma_j=M\Big((C-S)(C-S)^T+[N]_\times^2\Big)\delta_j.
\]

并且

\[
\frac{\partial E^*_{ij}}{\partial C}= -\frac{\partial E^**{ij}}{\partial S}=(C-S)^TA*{ij},
\]

\[
\frac{\partial E^**{ij}}{\partial N}=N^T\Big(A*{ij}-(2M_i^TM_j)I_3\Big),
\]

其中

\[
A_{ij}=M_iM_j^T+M_jM_i^T.
\]

对圆环模型，只需在外、内两条分支中分别代入

\[
N\leftarrow \rho_{\text{out}}n,
\qquad
N\leftarrow \rho_{\text{in}}n,
\]

其余 Jacobian 不变。若以 \(n\) 为优化变量，则由链式法则直接得到

\[
\frac{\partial F_{j,k}}{\partial n}
=\rho_k\,\frac{\partial F}{\partial N}\Big|_{N=\rho_kn}.
\]

因此，**圆环模型并不需要重新推导新的透视 Jacobian；只需要把 GH 的单圆 Jacobian 作为“分支模板”复制两份，然后用已知半径进行代入即可。**

### 6.7 联合 GH 的解算方式

和 GH(2014) 一样，把所有视图与所有分支联立后，构造非线性 GH 模型，在每次迭代中共同修正：

- 双边界的 \(\operatorname{vec5}(E^*)\) 观测；
- 相机位姿观测；
- 目标几何未知量 \(X\)。

最后得到：

1. 调整后的 3D 中心 \(\hat C\)；
2. 调整后的法向 \(\hat n\)（或等价的 \(\hat N_{\text{out}},\hat N_{\text{in}}\)）；
3. 调整后的相机位姿；
4. 对应协方差矩阵。

这就是严格意义上的“多视图联合 GH 同心双圆解”。

---

## 7. 不确定度传播：从双对偶椭圆到 3D 圆环几何

### 7.1 前端协方差

对于每个视图、每条边界，前端都已给出

\[
\Sigma_{j,\text{out}},\qquad \Sigma_{j,\text{in}}.
\]

若两条边界是完全独立拟合的，理论上可先近似写成块对角观测协方差：

\[
\Sigma_{L_j}
\approx
\operatorname{diag}
\big(
\Sigma_{\text{pose},j},
\Sigma_{j,\text{out}},
\Sigma_{j,\text{in}}
\big).
\]

若内外边界共享同一检测器并在同一步估计，则严格说还应包含交叉协方差块

\[
\Sigma_{j,\text{out,in}}.
\]

这是“纯理论最严谨”和“工程近似最常见”之间的分界线：

- **纯理论最严谨**：保留交叉协方差；
- **工程近似最常见**：先取块对角。

### 7.2 后端协方差

GH(2014) 的原则仍然成立：最终未知量协方差由收敛点处的 GH 法方程逆矩阵给出。若使用 \(X=(C,n)\)，则可得到

\[
\Sigma_{\hat X}=
\begin{bmatrix}
\Sigma_{\hat C} & \Sigma_{\hat C\hat n}\\
\Sigma_{\hat n\hat C} & \Sigma_{\hat n}
\end{bmatrix}.
\]

如果需要恢复“半径缩放法向量”的协方差，则由一阶传播

\[
\Sigma_{\hat N_{\text{out}}}=\rho_{\text{out}}^2\Sigma_{\hat n},
\qquad
\Sigma_{\hat N_{\text{in}}}=\rho_{\text{in}}^2\Sigma_{\hat n}.
\]

如果还想得到任一视图上预测对偶椭圆的后验协方差，则可进一步做线性传播：

\[
\Sigma_{\operatorname{vec5}(E^**{j,k})}
\approx
J*{X,j,k}\Sigma_{\hat X}J_{X,j,k}^T
+
J_{\text{pose},j,k}\Sigma_{\text{pose},j}J_{\text{pose},j,k}^T.
\]

这一步对误差椭圆、可观性分析和靶标/相机布局优化都很重要。

---

## 8. 为什么圆环靶标理论上可以比 GH(2014) 单圆更精？

答案是：**可以，但不是无条件。**

### 8.1 信息量增加：每视图从 5 个对偶椭圆约束增加到 10 个

GH(2014) 的单圆，每个视图只贡献一条
\(\operatorname{vec5}(E^*)\) 约束；圆环则贡献两条。即使不利用同心几何，仅从“残差块数量翻倍”这一点看，联合估计的观测信息也更强。

### 8.2 已知半径把尺度自由度进一步压紧

GH(2014) 的单圆模型中，\(N\) 的模长就是半径。你的问题里，内外圆半径是制造已知量，因此模型不仅多了第二条分支，还多了**已知尺度先验**。这会显著压缩目标几何的不确定度，尤其是法向方向与中心耦合较强的情形。

### 8.3 同心双圆的单视图投影几何能帮助剔除偏差与错误初始化

Wang(2019) 的投影圆心/半径比、Huang(2015) 的 self-polar triangle、Hao(2021) 的椭圆中心共线，都会在前端提供“只有双圆才有”的一致性检查。这意味着：

- 更少的误匹配；
- 更稳的初始化；
- 更少把“椭圆中心”误当“圆心投影”的系统性错误。

### 8.4 位姿改正会同时被两条边界约束

在 GH 联合求解中，位姿是公共变量。单圆时每视图只有一条椭圆去约束位姿改正；圆环时外圆和内圆同时约束同一位姿改正，因此后端对相机外参误差通常更敏感，也更容易被收缩。

### 8.5 但网络几何仍然是第一主因

GH(2014) 自己的仿真实验已经表明：相机布局对精度影响极大，非共面的相机网络明显优于几乎共面的布局。圆环模型不会改变这一事实。也就是说：

- **好的圆环 + 坏的相机几何**，未必优于好的单圆 + 好的相机几何；
- **好的圆环 + 好的相机几何**，通常才会显著优于 GH(2014) 的单圆设置。

### 8.6 反光内圆可能引入系统偏差，抵消理论增益

你的内圆是反光颜料，这意味着内边界可能出现：

- 高光饱和；
- 边缘局部缺失；
- 非高斯误差；
- 亚像素轮廓偏置。

GH/最小二乘理论提升依赖于“额外观测是正确建模的”。如果内圆边界带来的是**系统偏差**而非小方差随机噪声，那么“多一条边界”不一定提高精度，甚至可能拉低精度。因此理论上最优的做法不是无脑等权，而是：

- 前端对内、外边界分别估计协方差；
- 在联合 GH 中严格按协方差加权；
- 必要时对内边界采用鲁棒权或剔除策略。

### 8.7 结论性判断

因此，对“是否能比论文更高精度”这个问题，最准确的理论回答是：

> **能。** 在以下条件同时成立时，圆环靶标的同心双圆联合 GH，理论上应优于 GH(2014) 的单圆方案：
>
> 1. 内外边界都可被无偏提取；
> 2. 已知内外径在模型中被显式利用；
> 3. 采用双分支联合 GH，而不是两次独立单圆重建后再简单平均；
> 4. 相机网络具有良好基线与非退化交会几何；
> 5. 畸变和位姿不确定度被正确建模。
>
> 若内圆反光造成明显系统偏差、镜头畸变未充分补偿或视角网络接近退化，则提升不再有保证。

---

## 9. 对应的近似工程实现

下面给出一条“尽量贴近理论、但可落地”的工程版本。它不改变理论链条，只对难以一次做到最优的环节做近似。

### 9.1 建议流程

#### Step 1：图像预处理与候选区域检测

- 对圆环目标做 ROI 提取；
- 若场景复杂，可直接使用 **CCTag** 风格的同心环检测前端；
- 若目标外观简单，也可用 OpenCV 轮廓提取 + 边缘分组。

#### Step 2：内外边界椭圆初始化

分别对内、外边界用

- `fitEllipseDirect`（Fitzgibbon 类直接法），或
- `fitEllipseAMS`

做初值估计。

#### Step 3：GH 二维椭圆精化与协方差传播

把初始化结果送入 GH(2014) 的二维椭圆 GH 模型，得到

\[
\operatorname{vec5}(E^**{j,\text{out}}),\;\Sigma*{j,\text{out}},
\qquad
\operatorname{vec5}(E^**{j,\text{in}}),\;\Sigma*{j,\text{in}}.
\]

#### Step 4：单视图同心一致性检查

在每个视图上做三类检查：

1. **Wang(2019)**：由 \(Q_2Q_1^{-1}\) 求真实投影圆心和半径比；
2. **Hao(2021)**：检查两个椭圆中心与真实投影圆心共线；
3. **已知半径比检查**：估计到的 \(R/r\) 应接近制造已知值。

不通过者降权或剔除。

#### Step 5：多视图联合 GH 后端

把每个视图的

- 位姿观测及其协方差；
- 外边界 \(\operatorname{vec5}(E^*)\) 及协方差；
- 内边界 \(\operatorname{vec5}(E^*)\) 及协方差

全部送入双分支 GH 后端，联合求解 \(C\)、法向及位姿改正。

#### Step 6：输出与质量评估

输出

- 每幅图的内外 \(\operatorname{vec5}(E^*)\) 与协方差；
- 多视图联合后的 \(\hat C\)、\(\hat n\)（或 \(\hat N_{\text{out}},\hat N_{\text{in}}\)）；
- 后验协方差；
- 残差统计；
- 单视图半径比一致性与投影圆心残差。

### 9.2 哪些地方是“工程近似”而非严格理论

1. **内外边界协方差通常先按块对角处理**：严格理论上应保留交叉协方差；
2. **先 OpenCV 初始化再 GH 精化**：属于数值实现策略，而非理论必要；
3. **后端可用 Ceres/g2o 近似实现 GH**：真正严格的 GH 需要显式处理观测修正与权矩阵；工程上常用等价残差最小化近似；
4. **对反光内圆可能需要鲁棒核/异常值拒绝**：这是为了抑制系统偏差，不属于 GH 原始理论的一部分。

---

## 10. 可直接利用的开源实现与它们各自能覆盖到哪一步

| 组件 | 类型 | 能覆盖的环节 | 优点 | 局限 |
|---|---|---|---|---|
| OpenCV `fitEllipseDirect` / `fitEllipseAMS` | 通用视觉库 | 椭圆初始化 | 易用、成熟、速度快 | 不直接给 GH 协方差传播 |
| CCTag | 专用同心环检测库 | 同心环检测、公共圆心定位 | 对运动模糊/恶劣条件鲁棒，适合圆环靶前端 | 不提供 GH 多视图不确定度后端 |
| RUNE-Tag | fiducial 系统 | 基于圆形高对比特征的识别与位姿估计 | 有现成 marker 生态 | 不是为 GH 圆重建与协方差传播设计 |
| Danaozhong / 3D-Circle-Reconstruction-from-2D-Ellipses | 示例代码 | 单圆 3D 重建参考 | 便于理解单圆多视图重建代码结构 | 未形成“同心双圆 + 不确定度 + 联合 GH”完整链 |

**实际建议**：

- 前端：优先考虑 **CCTag/OpenCV**；
- 中间层：自行实现 GH(2014) 的 2D 椭圆协方差传播；
- 后端：自行实现“双分支联合 GH”；
- 若赶进度：用 Ceres 先做一个“近似 GH”版本验证几何正确性，再回到严格 GH 权矩阵与观测修正。

---

## 11. 一个推荐的理论—工程双轨方案

### 11.1 纯理论主链（推荐写论文/设计系统时采用）

1. 按 GH(2014) 分别拟合内、外椭圆，输出双 \(\operatorname{vec5}(E^*)\) 与双协方差；
2. 用 Wang(2019)、Huang(2015)、Hao(2021) 做单视图同心几何一致性校验；
3. 用 GH(2014) 的 3D 圆投影方程复制成内/外两条分支；
4. 用已知 \(\rho_{\text{out}},\rho_{\text{in}}\) 把两条分支共享到同一组 3D 几何未知量上；
5. 用联合 GH 同时调整内外椭圆与相机位姿，输出后验协方差；
6. 用后验协方差评估相机布局与网络稳定性。

### 11.2 近似工程主链（推荐快速落地）

1. OpenCV/CCTag 找到内外边界；
2. OpenCV 给椭圆初值；
3. GH 二维椭圆精化并估计协方差；
4. 用 Wang(2019) 做投影圆心和半径比过滤；
5. 用 Ceres 写双分支重投影残差；
6. 初版协方差先用高斯近似/数值 Hessian；
7. 功能跑通后，再替换为严格 GH。

---

## 12. 结论

从纯理论角度看，你的问题并不需要推翻 GH(2014)，也不需要重新发明“圆在透视下的投影方程”。最合理的路线是：

- **前端**继续使用 GH(2014) 的二维椭圆 GH 拟合与不确定度传播；
- **中层**加入同心双圆的单视图投影几何（Wang / Huang / Hao）做一致性检查与更优初始化；
- **后端**把 GH(2014) 的单圆方程复制为内圆与外圆两条分支，再用已知半径和共同法向把它们耦合为一个联合 GH 系统。

因此，对“是否能取得比论文所述更高的精度”的最终回答是：

1. **理论上可以，而且很有希望。**
2. **真正的增益来自三件事同时发生**：双边界观测、已知内外径先验、联合 GH 权矩阵。
3. **若只把它当作‘两个独立单圆’而不做同心耦合，提升会明显打折。**
4. **若反光内圆引入系统偏差而未建模，理论增益可能被完全抵消。**

也就是说，最值得实现的不是“多测一条椭圆”，而是**把同心双圆的全部投影几何与不确定度结构，完整地并入 GH(2014) 的多视图后端。**

---

## 参考文献

1. Soheilian, B., & Brédif, M. (2014). *Multi-view 3D Circular Target Reconstruction with Uncertainty Analysis*. ISPRS Annals of the Photogrammetry, Remote Sensing and Spatial Information Sciences, II-3, 143–148. DOI: 10.5194/isprsannals-II-3-143-2014.
2. Hartley, R., & Zisserman, A. (2004). *Multiple View Geometry in Computer Vision* (2nd ed.). Cambridge University Press.
3. Fitzgibbon, A., Pilu, M., & Fisher, R. B. (1999). Direct least-squares fitting of ellipses. *IEEE TPAMI*, 21(5), 476–480.
4. Förstner, W. (2005). Uncertainty and projective geometry. In *Handbook of Geometric Computing*.
5. Quan, L. (1996). Conic reconstruction and correspondence from two views. *IEEE TPAMI*, 18(2).
6. Mai, F., Hung, Y. S., & Chesi, G. (2010). Projective reconstruction of ellipses from multiple images. *Pattern Recognition*, 43(3), 545–556.
7. Bergamasco, F., Cosmo, L., Albarelli, A., & Torsello, A. (2012). A Robust Multi-camera 3D Ellipse Fitting for Contactless Measurements. *3DIMPVT 2012*.
8. Jiang, G., & Quan, L. (2005). Detection of Concentric Circles for Camera Calibration. *ICCV 2005*.
9. Huang, Z., Zhang, Z., & Cheung, Y. (2015). The Common Self-polar Triangle of Concentric Circles and Its Application to Camera Calibration. *CVPR 2015*.
10. Calvet, L., Gurdjos, P., Griwodz, C., & Gasparini, S. (2016). Detection and Accurate Localization of Circular Fiducials under Highly Challenging Conditions. *CVPR 2016*.
11. Wang, X., Chern, A., & Alexa, M. (2019). Center of circle after perspective transformation. arXiv:1902.04541.
12. Hao, et al. (2021). Conic tangents based high precision extraction method of concentric circle centers and its application in camera parameters calibration. *Scientific Reports*, 11, 21114.
13. Huo, et al. (2024). Iterative Camera Calibration Method Based on Concentric Circle Grids. *Applied Sciences*, 14(5), 1813.
14. OpenCV documentation: `fitEllipse`, `fitEllipseAMS`, `fitEllipseDirect`.
15. CCTag project: <https://github.com/alicevision/CCTag> and <https://cctag.readthedocs.io/>
16. RUNE-Tag project: <https://github.com/artursg/RUNEtag>
17. Danaozhong. *3D-Circle-Reconstruction-from-2D-Ellipses*: <https://github.com/Danaozhong/3D-Circle-Reconstruction-from-2D-Ellipses>

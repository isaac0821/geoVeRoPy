NAME SOCP
ROWS
 N  OBJ
 E  R0      
 E  R1      
 E  R2      
 E  R3      
 E  R4      
 E  R5      
 L  qc0     
 L  qc1     
 L  qc2     
COLUMNS
    x_1       R0        -1
    x_1       R2        1
    x_1       R4        -1
    y_1       R1        -1
    y_1       R3        1
    y_1       R5        -1
    d_0       OBJ       1
    d_1       OBJ       1
    dx_0      R0        1
    dy_0      R1        1
    dx_1      R2        1
    dy_1      R3        1
    rx_1      R4        1
    ry_1      R5        1
RHS
    RHS1      R0        -2.2096140435672424e+01
    RHS1      R1        -8.8131506327534517e+00
    RHS1      R2        4.0659321810277291e+01
    RHS1      R3        6.9958386545556039e+01
    RHS1      R4        -9.7401343692522758e+01
    RHS1      R5        -3.6407918171966955e+01
    RHS1      qc2       100
BOUNDS
 LO BND1      x_1       2.1096140435672424e+01
 UP BND1      x_1       1.0840134369252276e+02
 LO BND1      y_1       7.8131506327534517e+00
 UP BND1      y_1       7.0958386545556039e+01
 FR BND1      dx_0    
 FR BND1      dy_0    
 FR BND1      dx_1    
 FR BND1      dy_1    
 FR BND1      rx_1    
 FR BND1      ry_1    
QCMATRIX   qc0     
    d_0       d_0       -1
    dx_0      dx_0      1
    dy_0      dy_0      1
QCMATRIX   qc1     
    d_1       d_1       -1
    dx_1      dx_1      1
    dy_1      dy_1      1
QCMATRIX   qc2     
    rx_1      rx_1      1
    ry_1      ry_1      1
ENDATA

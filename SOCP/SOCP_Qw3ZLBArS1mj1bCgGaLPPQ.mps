NAME SOCP
ROWS
 N  OBJ
 E  R0      
 E  R1      
 E  R2      
 E  R3      
 E  R4      
 E  R5      
 E  R6      
 E  R7      
 E  R8      
 E  R9      
 L  qc0     
 L  qc1     
 L  qc2     
 L  qc3     
 L  qc4     
COLUMNS
    x_1       R0        -1
    x_1       R2        1
    x_1       R6        -1
    y_1       R1        -1
    y_1       R3        1
    y_1       R7        -1
    x_2       R2        -1
    x_2       R4        1
    x_2       R8        -1
    y_2       R3        -1
    y_2       R5        1
    y_2       R9        -1
    d_0       OBJ       1
    d_1       OBJ       1
    d_2       OBJ       1
    dx_0      R0        1
    dy_0      R1        1
    dx_1      R2        1
    dy_1      R3        1
    dx_2      R4        1
    dy_2      R5        1
    rx_1      R6        1
    ry_1      R7        1
    rx_2      R8        1
    ry_2      R9        1
RHS
    RHS1      R0        -50
    RHS1      R1        -50
    RHS1      R4        50
    RHS1      R5        50
    RHS1      R6        -2.7935270924026923e+00
    RHS1      R7        -8.1913540490470979e+01
    RHS1      R8        -94.5634959346547
    RHS1      R9        -2.2884668127303620e+01
    RHS1      qc3       100
    RHS1      qc4       100
BOUNDS
 LO BND1      x_1       -8.2064729075973073e+00
 UP BND1      x_1       1.0556349593465470e+02
 LO BND1      y_1       1.1884668127303620e+01
 UP BND1      y_1       9.2913540490470979e+01
 LO BND1      x_2       -8.2064729075973073e+00
 UP BND1      x_2       1.0556349593465470e+02
 LO BND1      y_2       1.1884668127303620e+01
 UP BND1      y_2       9.2913540490470979e+01
 FR BND1      dx_0    
 FR BND1      dy_0    
 FR BND1      dx_1    
 FR BND1      dy_1    
 FR BND1      dx_2    
 FR BND1      dy_2    
 FR BND1      rx_1    
 FR BND1      ry_1    
 FR BND1      rx_2    
 FR BND1      ry_2    
QCMATRIX   qc0     
    d_0       d_0       -1
    dx_0      dx_0      1
    dy_0      dy_0      1
QCMATRIX   qc1     
    d_1       d_1       -1
    dx_1      dx_1      1
    dy_1      dy_1      1
QCMATRIX   qc2     
    d_2       d_2       -1
    dx_2      dx_2      1
    dy_2      dy_2      1
QCMATRIX   qc3     
    rx_1      rx_1      1
    ry_1      ry_1      1
QCMATRIX   qc4     
    rx_2      rx_2      1
    ry_2      ry_2      1
ENDATA

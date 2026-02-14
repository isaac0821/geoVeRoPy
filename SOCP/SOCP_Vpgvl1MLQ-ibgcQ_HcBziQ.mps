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
    RHS1      R0        -9.2317885005882587e+00
    RHS1      R1        -7.4261822411264049e+01
    RHS1      R2        90.6803331721131
    RHS1      R3        5.9795869266248268e+01
    RHS1      R4        -3.9953462297940270e+01
    RHS1      R5        -7.9933443466653870e+01
    RHS1      qc2       100
BOUNDS
 LO BND1      x_1       8.2317885005882587e+00
 UP BND1      x_1       91.6803331721131
 LO BND1      y_1       5.8795869266248268e+01
 UP BND1      y_1       9.0933443466653870e+01
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

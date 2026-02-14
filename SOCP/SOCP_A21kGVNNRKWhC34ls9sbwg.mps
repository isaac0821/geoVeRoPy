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
 E  R10     
 E  R11     
 E  R12     
 E  R13     
 E  R14     
 E  R15     
 E  R16     
 E  R17     
 L  qc0     
 L  qc1     
 L  qc2     
 L  qc3     
 L  qc4     
 L  qc5     
 L  qc6     
 L  qc7     
 L  qc8     
COLUMNS
    x_1       R0        -1
    x_1       R2        1
    x_1       R10       -1
    y_1       R1        -1
    y_1       R3        1
    y_1       R11       -1
    x_2       R2        -1
    x_2       R4        1
    x_2       R12       -1
    y_2       R3        -1
    y_2       R5        1
    y_2       R13       -1
    x_3       R4        -1
    x_3       R6        1
    x_3       R14       -1
    y_3       R5        -1
    y_3       R7        1
    y_3       R15       -1
    x_4       R6        -1
    x_4       R8        1
    x_4       R16       -1
    y_4       R7        -1
    y_4       R9        1
    y_4       R17       -1
    d_0       OBJ       1
    d_1       OBJ       1
    d_2       OBJ       1
    d_3       OBJ       1
    d_4       OBJ       1
    dx_0      R0        1
    dy_0      R1        1
    dx_1      R2        1
    dy_1      R3        1
    dx_2      R4        1
    dy_2      R5        1
    dx_3      R6        1
    dy_3      R7        1
    dx_4      R8        1
    dy_4      R9        1
    rx_1      R10       1
    ry_1      R11       1
    rx_2      R12       1
    ry_2      R13       1
    rx_3      R14       1
    ry_3      R15       1
    rx_4      R16       1
    ry_4      R17       1
RHS
    RHS1      R0        -50
    RHS1      R1        -50
    RHS1      R8        50
    RHS1      R9        50
    RHS1      R10       -2.7935270924026923e+00
    RHS1      R11       -8.1913540490470979e+01
    RHS1      R12       -9.7401343692522758e+01
    RHS1      R13       -3.6407918171966955e+01
    RHS1      R14       -3.9953462297940270e+01
    RHS1      R15       -7.9933443466653870e+01
    RHS1      R16       -94.5634959346547
    RHS1      R17       -2.2884668127303620e+01
    RHS1      qc5       100
    RHS1      qc6       100
    RHS1      qc7       100
    RHS1      qc8       100
BOUNDS
 LO BND1      x_1       -8.2064729075973073e+00
 UP BND1      x_1       1.0840134369252276e+02
 LO BND1      y_1       1.1884668127303620e+01
 UP BND1      y_1       9.2913540490470979e+01
 LO BND1      x_2       -8.2064729075973073e+00
 UP BND1      x_2       1.0840134369252276e+02
 LO BND1      y_2       1.1884668127303620e+01
 UP BND1      y_2       9.2913540490470979e+01
 LO BND1      x_3       -8.2064729075973073e+00
 UP BND1      x_3       1.0840134369252276e+02
 LO BND1      y_3       1.1884668127303620e+01
 UP BND1      y_3       9.2913540490470979e+01
 LO BND1      x_4       -8.2064729075973073e+00
 UP BND1      x_4       1.0840134369252276e+02
 LO BND1      y_4       1.1884668127303620e+01
 UP BND1      y_4       9.2913540490470979e+01
 FR BND1      dx_0    
 FR BND1      dy_0    
 FR BND1      dx_1    
 FR BND1      dy_1    
 FR BND1      dx_2    
 FR BND1      dy_2    
 FR BND1      dx_3    
 FR BND1      dy_3    
 FR BND1      dx_4    
 FR BND1      dy_4    
 FR BND1      rx_1    
 FR BND1      ry_1    
 FR BND1      rx_2    
 FR BND1      ry_2    
 FR BND1      rx_3    
 FR BND1      ry_3    
 FR BND1      rx_4    
 FR BND1      ry_4    
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
    d_3       d_3       -1
    dx_3      dx_3      1
    dy_3      dy_3      1
QCMATRIX   qc4     
    d_4       d_4       -1
    dx_4      dx_4      1
    dy_4      dy_4      1
QCMATRIX   qc5     
    rx_1      rx_1      1
    ry_1      ry_1      1
QCMATRIX   qc6     
    rx_2      rx_2      1
    ry_2      ry_2      1
QCMATRIX   qc7     
    rx_3      rx_3      1
    ry_3      ry_3      1
QCMATRIX   qc8     
    rx_4      rx_4      1
    ry_4      ry_4      1
ENDATA

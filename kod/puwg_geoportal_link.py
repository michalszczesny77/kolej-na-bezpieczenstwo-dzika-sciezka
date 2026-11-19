import math,sys
def to2180(lat,lon):
    a=6378137.0;f=1/298.257222101;e2=f*(2-f);ep2=e2/(1-e2);k0=0.9993;lon0=math.radians(19)
    p=math.radians(lat);l=math.radians(lon)
    N=a/math.sqrt(1-e2*math.sin(p)**2);T=math.tan(p)**2;C=ep2*math.cos(p)**2;A=(l-lon0)*math.cos(p)
    e4=e2*e2;e6=e4*e2
    M=a*((1-e2/4-3*e4/64-5*e6/256)*p-(3*e2/8+3*e4/32+45*e6/1024)*math.sin(2*p)+(15*e4/256+45*e6/1024)*math.sin(4*p)-(35*e6/3072)*math.sin(6*p))
    x=k0*N*(A+(1-T+C)*A**3/6+(5-18*T+T*T+72*C-58*ep2)*A**5/120)+500000
    y=k0*(M+N*math.tan(p)*(A*A/2+(5-T+9*C+4*C*C)*A**4/24+(61-58*T+T*T+600*C-330*ep2)*A**6/720))-5300000
    return x,y
lat,lon=float(sys.argv[1]),float(sys.argv[2]);x,y=to2180(lat,lon);r=150
print(f"https://mapy.geoportal.gov.pl/imap/Imgp_2.html?gpmap=gp0&bbox={x-r:.0f},{y-r:.0f},{x+r:.0f},{y+r:.0f}&variant=ORTOFOTOMAPA")

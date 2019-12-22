# Aashish N. Adhikari, 2018

# This script 

#arg1 = tsv file containing annotated variants generated by vcftotsv module of Varant software
#arg2 = param list file (tsv) - id column as the name - keep headers in params fixed
#arg3 = full path to folder to create and write output to

# To run:
# python PipelineMain.py arg1 arg2 arg3

import pandas as pd 
import numpy as np 
import re
import sys
from collections import Counter
import os

rootdir=sys.argv[3]
if not os.path.exists(rootdir):
	    os.mkdir(rootdir)

df = pd.read_csv(sys.argv[1], sep="\t")

df.fillna('0', inplace=True)
#Only consider columns with valid sample names
df=df[df["sample"]!="0"]

#
df['kgaf']=df['kgaf'].replace(['.','.,.'], '0.0')
df['espaf']=df['espaf'].replace(['.','.,.'], '0.0')
df['exacaf']=df['exacaf'].replace(['.','.,.'], '0.0')
df['kgaf']=df['kgaf'].astype(str).apply(lambda x: min(map(float,(x.split(',')))))
df['espaf']=df['espaf'].astype(str).apply(lambda x: min(map(float,(x.split(',')))))
df['exacaf']=df['exacaf'].astype(str).apply(lambda x: min(map(float,(x.split(',')))))


df['rf_score']=df['rf_score'].replace(['.','.,.','NA'], '0.0')
df.rf_score = df.rf_score.astype(float)

df['clnsig']=df.clnsg170907.astype(str)
df['clnstar']=df.clinstars170907.astype(str)

gts=['ug.gt','hc.gt','pp.gt']
hcug=['ug.gt','hc.gt']

# Helper functions

# check if genotype is homozygous
def homozygous(genotype):
    if genotype=="0" or genotype=="NA" or genotype=="":  
        genotype='0/0'
    x=re.split('/|\|',genotype)   
    #x=genotype.split("/")
    if x[0] != "0" and x[1] != "0":
        return True
    
# check if genotype is heterozygous
def heterozygous(genotype):
    if genotype=="0" or genotype=="NA" or genotype=="": 
        genotype='0/0'
    #x=genotype.split("/")
    x=re.split('/|\|',genotype)   
    if x[0] != x[1]:
        return True
    else: return False

def alleq(givenlist):
    homval='0/0'
    hetval='0/0'
    for i in givenlist:
        if (not heterozygous(i)) and (not homozygous(i)):
            return '0/0'
        else:
            if heterozygous(i):
                hetval=i
            elif homozygous(i): 
                homval=i
    if hetval != '0/0': return hetval
    elif homval != '0/0': return homval
    else: return '0/0'

def anyeq(givenlist):
    homval='0/0'
    hetval='0/0'
    for i in givenlist:
        if heterozygous(i): 
            hetval=i
        elif homozygous(i): 
            homval=i
    if homval != '0/0': return homval
    else: return hetval
    
def genocount(geno):
    homcount=0
    hetcount=0
    for i in geno:
        #print i 
        #g=i.split("/")
        g=re.split('/|\|',i)   
        if i != "0":
            if g[0] != "0"  and g[1] != "0":
                homcount += 1
            if g[0] == "0" or g[1] == "0" :
                hetcount += 1
    return homcount,hetcount

def genolistcount(genolist):
    for i in genolist:
        print genocount(str(i))
        

# Data prep
df['any.gt']=df[gts].apply(anyeq,axis=1)
df['all.gt']=df[gts].apply(alleq,axis=1)
df['hcORug.gt']=df[hcug].apply(anyeq,axis=1)

df['any.MAF']=df[['kgaf','espaf','exacaf']].apply(lambda x: x.min(), axis=1)
df['all.MAF']=df[['kgaf','exacaf']].apply(lambda x: x.max(), axis=1)

df['cadd'] = df['cadd'].astype(str)
df['cadd']=df['cadd'].replace(['N,A', '.'], '0')
df['cadd']=df['cadd'].replace([',.'], ',0',regex=True)
df['cadd']=df['cadd'].replace(['.,'], '0,',regex=True)
df['cadd']=df['cadd'].apply(lambda x: max(map(float,(x.split(',')))))

df['cadd'] = df['cadd'].astype(float)
df['meta_svmNum'] = df.meta_svm.apply(lambda x: 1.0 if x.startswith('D') else 0.0)

df['caddNonSyn']= df.apply(lambda row: row['cadd'] if (row['mutation']=="NonSyn") else 0.0, axis=1)
df['meta_svmNonSyn']= df.apply(lambda row: 1.0 if (row['mutation']=="NonSyn" and row["meta_svmNum"]==1.0) else 0.0, axis=1)

df['mutpred2']=df['meta_svmNonSyn']
df['mutpred2NonSyn']= df.apply(lambda row: row['mutpred2'] if (row['mutation']=="NonSyn") else 0.0, axis=1)


PA=['NonSyn', 'StartGain', 'StopGain', 'StartLoss', 'StopLoss', 'FrameShiftInsert', 'FrameShiftDelete', 'NonFrameShiftInsert', 'NonFrameShiftDelete' , 'SpliceDonor' ,'SpliceAcceptor']
PAlistunacc=[ 'StartLoss', 'StopLoss', 'NonFrameShiftInsert', 'NonFrameShiftDelete']
clintouse=['5','4']
HGMDtouse=['DM']
closetosplice=['Close_to_SpliceDonor', 'Close_to_SpliceAcceptor']
clinstartouse=['0', '1', '2|2', '1.0', '2|-|2|-', '1|-|1|-', '1|1', '1|-', '2|2|2', '2|2|2|2', '1|1|1', '1', '2', '-']
PAany=pd.unique(df[['mutation','splice']].values.ravel()).tolist()




# Function for filtering the variants based on pipeline parameters
def genpie2(genelist,transcript,callergt,gqthres,mafPAdb,mafPA, mafHGMDdb, mafHGMD,clinVar,clinstar,HGMD,PAval,removeoverlap,whichtoremove,onlyrecessive,outname,**options):
    

    if HGMD!="und":
        HGMD=eval(HGMD)
        print HGMD
    if PAval!="und":
        PAval=eval(PAval)
    if clinVar!="und":
        clinVar=eval(clinVar)
    if clinstar!="und":
        clinstar=eval(clinstar)

    mafPAx=0.0003
    mafHGMDx=0.0003

    #setting up MAF for X chromosome (roughly MAFx = 2 * q^2 , where q is MAF for automosomal alleles. If MAFX < 0.0003, set it up to MAFx = 0.00026 which is 1 allele in 1000 genomes).
    if mafPA != 'und':
            mafPA=float(mafPA)
            print "mafPA is",mafPA,type(mafPA)
	    mafPAx= 2*mafPA*mafPA
    if mafHGMD != 'und':
            mafHGMD=float(mafHGMD)
            print "mafHGMD is",mafHGMD,type(mafHGMD)
	    mafHGMDx=2*mafHGMD*mafHGMD

    if mafPAx < 0.0003:
	    mafPAx = 0.0003
    if mafHGMDx < 0.0003:
	    mafHGMDx = 0.0003

    print mafPAx, mafHGMDx

   
    pathogencriteria1=False
    if "pathogen1" in options and "pathogenscore1" in options:
        pathogen1=options.get("pathogen1")
        if pathogen1 != "und":
            pathogenscore1=float(options.get("pathogenscore1"))
            pathogencriteria1 = df[pathogen1].map(lambda x: x > pathogenscore1) 
        
    pathogencriteria2=False
    if "pathogen2" in options and "pathogenscore2" in options:
        pathogen2=options.get("pathogen2")
        if pathogen2 != "und":
            pathogenscore2=float(options.get("pathogenscore2"))
            pathogencriteria2 = df[pathogen2].map(lambda x: x > pathogenscore2) 
        
    pathogencriteria3=False
    if "pathogen3" in options and "pathogenscore3" in options:
        pathogen3=options.get("pathogen3")
        if pathogen3 != "und":
            pathogenscore3=float(options.get("pathogenscore3"))
            pathogencriteria3 = df[pathogen3].map(lambda x: x > pathogenscore3)
            
    lofteecriteria=False
    if "loftee" in options:
        lofteeval=options.get("loftee")
        if lofteeval=="Y":
            lofteecriteria= df['loftee'].map(lambda x: x=="y")
   
    genelistlist=open(genelist,"r").read().splitlines()

    genecriteria = df['gene'].map(lambda x: x in genelistlist)
    transcriptcriteria= (df[transcript]=="y")|(df[transcript]=="Y")|(df[transcript]=="yy")
    callercriteria = df[callergt].map(lambda x: str(x) != "0" and str(x) != "0/0")
    qualitycriteria = df['hc.gq']>gqthres

    clinvarcrit=False
    if clinVar!="und":
        print "clinvar is",clinVar,type(clinVar)
        clinvarcrit= df.clnsig.map(lambda x: not set(re.split('[,|]',x)).isdisjoint(set(clinVar)))

    clinstarcrit=False
    if clinstar!="und":
        refs=[m+":"+n for m in clinVar for n in clinstar]
        clinstarcrit=df.apply(lambda x: not set([m+":"+n for m,n in zip(re.split('[,|]',x['clnsig']),re.split('[,|]',x['clnstar']))]).isdisjoint(set(refs)),axis=1) 
    
    clinvarcriteria=clinvarcrit & clinstarcrit
    
    #gene filter
    df2=df[genecriteria]
    
    #transcript filter
    df2=df2[transcriptcriteria]
    
    #caller filter
    df2=df2[callercriteria]
    
    # quality filter
    df2=df2[qualitycriteria]

    # Included variants 
    includecriteria=False
    if "includefile" in options:
        includefilen=options.get("includefile")
        if includefilen != 'und':
            includedftemp=pd.read_csv(includefilen, sep="\t")
            #print includedftemp
            includedftemp.chrom = includedftemp.chrom.astype(str)
            keys=['chrom', 'pos', 'ref', 'alt']
            includecriteria=True
            includedf=pd.merge(df2,includedftemp[keys],how='inner',on=keys)
            #print includedf
    
    #Excluded variant list
    excludecriteria=False
    if "excludefile" in options:
        excludefilen=options.get("excludefile")
        if excludefilen != 'und':
            excludedftemp=pd.read_csv(excludefilen, sep="\t")
            excludedftemp.chrom = excludedftemp.astype(str)
            keys=['chrom', 'pos', 'ref', 'alt']
            excludecriteria=True
            df2i = df2.set_index(keys)
            other2 = excludedftemp.set_index(keys)
            df2=df2[~df2i.index.isin(other2.index)]

    
    #LeftArm and RightArm loading
    leftarm = False
    rightarm = False
    if mafPA != "und":
        leftarm=((  ( (df2[mafPAdb] <= mafPA) & (df2['chrom'] != "X") ) | (   (df2[mafPAdb] <= mafPAx) & (df2['chrom']=="X")) )  & ((df2['mutation'].isin(PAval)) | (df2['splice'].isin(PAval)) | pathogencriteria1 | pathogencriteria2 | pathogencriteria3 | lofteecriteria))
    
    print mafHGMD, mafHGMDx, HGMD

    if mafHGMD != "und":
        print "MAF HGMD defined"
        rightarm=(    (   ( (df2[mafHGMDdb] <= mafHGMD) & (df2['chrom'] != "X") ) | ( (df2[mafHGMDdb] <= mafHGMDx) & (df2['chrom']=="X") ) )  & ((clinvarcriteria) | (df2['hgmdvar'].isin(HGMD))))
 
    #Allow variants that pass either the left or the right arm
    df2=df2[ leftarm | rightarm ]
    
    #Merge variants from the inlcude list to the dataframe
    if includecriteria:
        df2=pd.merge(df2,includedf,how='outer')

    #Removing a variant that are within close to another variant  another variant 
    df2.sort(['sample','chrom','pos'], inplace=True)

    if whichtoremove=='first':
        df2['dpos'] = np.abs(df2['pos'] - df2['pos'].shift(-1))
	df2['dsample']=df2['sample']==df2['sample'].shift(-1
    
    elif whichtoremove=='second':
        df2['dpos'] = np.abs(df2['pos'] - df2['pos'].shift(1))
	df2['dsample']=df2['sample']==df2['sample'].shift(1)
    df2['dpos'].fillna(1000.0, inplace=True)
    df2['dsample'].fillna(False, inplace=True)
    
    df2=df2[(  (~((df2['dpos'] < removeoverlap) & (df2['dsample']==True))) | ~df2[callergt].str.contains('0') )]
    
    #save the gene calls in the gene call file
    outgene= rootdir + '/' + outname + '.gene'
    f1 = open(outgene, 'w')

    cnvcriteria=False
    if "cnvfile" in options:
        cnvfilen=options.get("cnvfile")
        if cnvfilen != 'und':
            cnvdf=pd.read_csv(cnvfilen, sep="\t")
            cnvcriteria=True


    if cnvcriteria:
            for index,row in cnvdf[(cnvdf['zygosity']>1) | (cnvdf['gene']=="OTC")].iterrows():
                print >> f1,row['sample'],row['gene'],"CNVhom"

    
    mat1avar=((df2['pos']==82034933) & (df2['chrom']=="10") & (df2['ref']=='C') & (df2['alt']=='T'))
    if includecriteria:
        for index,row in df2[mat1avar].iterrows():
            print >> f1,row['sample'], row['gene'], "Dominant"


    samples = df2.groupby("sample")
    tots={}

    #Count the number of filtered variants per sample and output those that fit recessive model
    for sample,cols in samples:
        x=cols.groupby('gene')[callergt].apply(genocount)
        tot=0
        for j,i in x.iteritems():
            if int(i[0]) > 0 or j=="OTC" :
                tot+=1
                print >> f1, sample, j, "Homozygous"
            if int(i[1]) > onlyrecessive:
                tot+=1
                print >> f1, sample, j, "CompHet"
            if cnvcriteria:
                cnvtemp=cnvdf.query('sample==@sample and gene==@j')
                if cnvtemp.shape[0]>0:
                    if int(i[1])+int(cnvtemp['zygosity'])>1:
                        tot+=1
                        print >> f1, sample, j, "CNVwithSNV"
        if tot>1: tot=2
        tots[sample]=tot
  
    c=Counter(tots.values())
    total=sum(c.values())
    
    zeromatch=[samp for samp, val in tots.items() if val == 0]
    onematch=[samp for samp, val in tots.items() if val == 1]
    twomatch=[samp for samp, val in tots.items() if val > 1]
    
    global df3
    df3=df2
    outvar=rootdir + '/' + outname + '.var'
    df3.to_csv(outvar,sep="\t")
    
    f1.close()  


# Reading pipeline parameters
params = pd.read_csv(sys.argv[2], sep="\t")
params.fillna('und', inplace=True)
for index, row in params.iterrows():
	print row
        genpie2(genelist=row.genelist,
                transcript=row.transcript,  
		callergt=row.caller, 
		gqthres=row.gqthres, 
		mafPAdb=row.maf_db, 
		mafPA=row.maf_thres, 
		mafHGMDdb=row.disease_maf_db, 
		mafHGMD=row.disease_maf_thres, 
		clinVar=row.clnvar, 
		clinstar=row.clnstar, 
                HGMD=row.hgmd, 
		PAval=row.pa_list, 
		removeoverlap=15, 
		whichtoremove='first', 
		onlyrecessive=1, 
		outname=row['id'], 
		pathogen1 = row.pathogen1 ,
		pathogenscore1 = row.pathogen1_score, 
		pathogen2 = row.pathogen2,
		pathogenscore2 = row.pathogen2_score,
		pathogen3=row.pathogen3,
		pathogenscore3=row.pathogen3_score,
		loftee=row.loftee,
		includefile=row.includefile,
		excludefile=row.excludefile,
		cnvfile=row.cnvfile
		)

#Required packages
library(ggplot2)
library(emmeans)
library(nlme)
library(tidyr)

#Load in dataframe
df <- read.csv("/athena/listonlab/scratch/dje4001/pseudorabies_dataset")

#Revised dataframe
df<-df[df$lv1!=df$location,]

#Prepare dataframe
df$uid<-paste(df$cage,df$subjectid,df$treatment) #Create unique identifier for each subject
st.err<-function(x){sd(x,na.rm=TRUE)/(sqrt(length(x)))}
df$treatment<-as.factor(df$treatment) 
levels(df$treatment)<-c("Vehicle","ChronicCORT") #rename levels
df_total_cells<-aggregate(n~uid,data=df,FUN="sum") #Generate total number of cells per brain for normalization
colnames(df_total_cells)[2]<-"total_cells"
df_aggregated<-aggregate(n~uid+treatment+lv8+lv4,data=df,FUN="sum")
df_aggregated<-df_aggregated[!(df_aggregated$n<=1),]#Threshold regions with only 1 cell in them
df_aggregated<-merge(df_aggregated,df_total_cells,by="uid")
df_aggregated$uid<-as.factor(df_aggregated$uid)
df_aggregated$lv8<-as.factor(df_aggregated$lv8)
df_aggregated$normalized_cell_count<-df_aggregated$n/df_aggregated$total_cells #Normalize by the total number of cells

# graph average +/- sem
g1<-aggregate(normalized_cell_count~lv8+treatment+lv4,FUN="mean",data=df_aggregated)
ge<-aggregate(normalized_cell_count~lv8+treatment+lv4,FUN=st.err,data=df_aggregated)
g1$error<-ge$normalized_cell_count
g1<-g1[!is.na(g1$error),]

p<-ggplot(data=g1,aes(x=normalized_cell_count,y=lv8,group=treatment,fill=treatment,color=treatment))+
  geom_errorbar(aes(xmax=normalized_cell_count+error,xmin=normalized_cell_count-error),linewidth=1,width=0)+
  geom_point(size=5,alpha=0.7)+
  geom_point(size=3,aes(color="white",fill="white"))+
  #geom_jitter(data=df_aggregated,aes(x=normalized_cell_count,y=location,fill=treatment,color=treatment),width=0)+
  theme(panel.grid.major = element_blank(), #panel.grid.minor = element_blank(),
        panel.background = element_blank(), axis.line = element_line(colour = "black")) + 
  #theme(legend.position = "none")+
  scale_colour_manual(values=c("red", "blue", "white"))+
  scale_fill_manual(values=c("red", "blue", "white"))+
  facet_wrap(.~lv4,scales="free")
print(p)
ggsave("/athena/listonlab/scratch/dje4001/normalized_cell_allregions.pdf",width=20,height=49.9999,dpi=100)

# Box plot and jitter
p<-ggplot(data=df_aggregated,aes(x=normalized_cell_count,y=location,fill=treatment,color=treatment))+
  geom_boxplot()+
  #geom_jitter()+
  theme(panel.grid.major = element_blank(), #panel.grid.minor = element_blank(),
        panel.background = element_blank(), axis.line = element_line(colour = "black")) + 
  #theme(legend.position = "none")+
  scale_colour_manual(values=c("blue", "red", "white"))+
  scale_fill_manual(values=c("blue", "red", "white"))
print(p)
ggsave("/athena/listonlab/scratch/dje4001/normalized_cell_allregions_boxplots.pdf",width=20,height=49.9999,dpi=100)


#Wide format of data
df_temp<-df_aggregated[,-4:-5]
dfwide_region<-spread(df_temp,lv8,normalized_cell_count)
dfwide_region[is.na(dfwide_region)]<-0
write.csv(dfwide_region,"/athena/listonlab/scratch/dje4001/dfwide_region.csv",row.names=FALSE)
df_av<-aggregate(normalized_cell_count~treatment+lv8,data=df_aggregated,FUN="mean")
dfwide<-spread(df_av,treatment,normalized_cell_count)


# Calculate P values and generate a new dataframe 
df_av<-aggregate(normalized_cell_count~treatment+lv8,data=df_aggregated,FUN="sd")
dfwide_sd<-spread(df_av,treatment,normalized_cell_count)

df_av<-aggregate(normalized_cell_count~treatment+lv8,data=df_aggregated,FUN="length")
dfwide_df<-spread(df_av,treatment,normalized_cell_count)

tvalue<-(dfwide[2]-dfwide[3])/sqrt(((dfwide_sd[2]^2)/dfwide_df[2])+((dfwide_sd[3]^2)/dfwide_df[3]))
degreesfreedom<-dfwide_df[2]+dfwide_df[3]-2
fc<-(dfwide[2]-dfwide[3])/dfwide[2]

pvals<-data.frame()
for(i in 1:nrow(tvalue)){
  p<-pt(q=tvalue[i,],df=degreesfreedom[i,],lower.tail=FALSE)
  pvals<-rbind(pvals,p)
}

volcano_data<-cbind(dfwide,fc,tvalue,degreesfreedom,pvals)
colnames(volcano_data)<-c("region","Vehicle", "Chronic CORT", "foldchange","tvalue","degreesf","p")
volcano_data$labels[volcano_data$p<0.07]<-(volcano_data$p<0.07)
volcano_data<-drop_na(volcano_data)

dfwide$CORTerror<-dfwide_sd$ChronicCORT
dfwide$Vehicleerror<-dfwide_sd$Vehicle

dfwide$VehicleN<-sqrt(dfwide_df$Vehicle+1)
dfwide$CORTN<-sqrt(dfwide_df$ChronicCORT+1)

dfwide$CORTse<-dfwide$CORTerror/dfwide$CORTN
dfwide$Vehiclese<-dfwide$Vehicleerror/dfwide$VehicleN

# Generate a volcano plot of fc + pvalues
library(ggrepel)
p<-ggplot(data=volcano_data,aes(group=region,x=log2(foldchange),y=-log10(p),color=-log10(p),fill=-log10(p),label=region))+
  geom_point(size=10,alpha=0.7)+
  #geom_text_repel(size=10)+
  theme(panel.grid.major = element_blank(), panel.grid.minor = element_blank(),
        panel.background = element_blank(), axis.line = element_line(colour = "black"))
print(p)
ggsave("/athena/listonlab/scratch/dje4001/volcano_plot.pdf",width=20,height=20,dpi=100)

#Distribution of FoldChange
p<-ggplot(data=dfwide,aes(x=(Vehicle-ChronicCORT),fill="green"))+
  geom_density(size=2)+
  #geom_vline(xintercept=0)+
  theme(panel.grid.major = element_blank(), panel.grid.minor = element_blank(),
        panel.background = element_blank(), axis.line = element_line(colour = "black"))+
  scale_fill_manual(values=c("#00cc00"))
print(p)
ggsave("/athena/listonlab/scratch/dje4001/residuals_dist.pdf",width=20,height=20,dpi=100)


#Average +/- SEM across subjects
df_av<-aggregate(normalized_cell_count~treatment+location,data=df_aggregated,FUN="mean")
df_err<-aggregate(normalized_cell_count~treatment+location,data=df_aggregated,FUN=st.err)
df_av$error<-df_err$normalized_cell_count

#Save average dataframe
write.csv(df_av,"/athena/listonlab/scratch/dje4001/pseudorabies_average.csv")


#Metrixs nessesary for linear model
#Distribution of cell counts per animal per region
p<-ggplot(data=df_aggregated,aes(x=normalized_cell_count,group=treatment,fill=treatment))+
  geom_density(alpha=0.5)+
  stat_boxplot(aes(fill=treatment,group=treatment),width=0.05)+
  xlab("log10(Normalized cell count)")+
  ylab("Kernel Density")+
  theme(panel.grid.major = element_blank(), panel.grid.minor = element_blank(),
        panel.background = element_blank(), axis.line = element_line(colour = "black"))+
  scale_colour_manual(values=c("blue", "red", "white"))+
  scale_fill_manual(values=c("blue", "red", "white"))
print(p)
ggsave("/athena/listonlab/scratch/dje4001/distribution_n.pdf",width=20,height=20,dpi=100)


#Main model
model1<-lme(log10(normalized_cell_count)~lv8*treatment,random=~1|uid,data=df_aggregated)

library(lme4)

#Model measures of fit
r<-data.frame(residuals(model1))
r$r<-as.numeric(r$r)
p<-ggplot(data=r,aes(x=1,y=r,color=r,fill=r))+geom_jitter(size=3,alpha=0.4,width=0.01)+
  geom_hline(yintercept=0,linetype="dashed",size=1)+
  ylab("Linear Mixed Effects Model Residuals")+
  theme(panel.grid.major = element_blank(), panel.grid.minor = element_blank(),
        panel.background = element_blank(), axis.line = element_line(colour = "black"),
        legend.position="none",axis.ticks.x=element_blank(),axis.text.x=element_blank(),axis.title.x=element_blank())
print(p)

#Plot a correlation of CORT and Vehicle
library(ggrepel)
volcano_data$color<-volcano_data$p<0.05
volcano_data$ChronicCORT<-volcano_data$'Chronic CORT'
p<-ggplot(data=volcano_data,aes(x=Vehicle,y=ChronicCORT,colour=color,fill=color))+
  #geom_errorbar(aes(xmin=Vehicle-Vehiclese,xmax=Vehicle+Vehiclese))+
  #geom_errorbar(aes(ymin=ChronicCORT-CORTse,ymax=ChronicCORT+CORTse))+
  geom_point(size=abs(volcano_data$foldchange)*10,shape=21,alpha=0.8)+
  #geom_point(size=5,aes(fill="white",colour="white"))+
  theme(legend.position = "none")+
  theme(panel.grid.major = element_blank(), panel.grid.minor = element_blank(),
        panel.background = element_blank(), axis.line = element_line(colour = "black"))+
  geom_text_repel(data=subset(volcano_data,p<0.05), aes(label=region),
                  size=5,
                  box.padding=unit(0.35,"lines"),
                  point.padding=unit(0.3,"lines"))+
  coord_trans(x="log10",y="log10")+
  #geom_abline(aes(slope=1,intercept=0,color="green"),size=2,linetype='dashed')+
  scale_fill_manual(values=c("black","red","white"))+
  scale_colour_manual(values=c("black", "red", "white"))
print(p)
ggsave("/athena/listonlab/scratch/dje4001/correlation_plot.pdf",width=20,height=20,dpi=100)



p<-ggplot(data=dfwide,aes(x=Vehicle,y=ChronicCORT,fill="black",colour="black"))+
  geom_bin_2d()+
  #theme(legend.position = "none")+
  theme(panel.grid.major = element_blank(), panel.grid.minor = element_blank(),
        panel.background = element_blank(), axis.line = element_line(colour = "black"))+
  #geom_text_repel(aes(label=location),
  #              size=5,
  #             box.padding=unit(0.35,"lines"),
  #            point.padding=unit(0.3,"lines"))+
  #coord_trans(x="log10",y="log10")+
  #geom_abline(aes(slope=1,intercept=0,colour="green"),size=2)+
  #scale_fill_manual(values=c("black","green","white"))+
  #scale_colour_manual(values=c("black", "green", "white"))
print(p)




#### OLDer

#Loop through plot over levels
p<-list()
for (i in colnames(df)){
  if (grepl("lv",i) || grepl("loc",i)){
    df_aggregated<-aggregate(n~uid+treatment+unlist(df[i]),data=df,FUN="sum") 
    df_aggregated_mean<-aggregate(n~treatment+unlist(df[i]),data=df,FUN="mean")
    df_aggregated_error<-aggregate(n~treatment+unlist(df[i]),data=df,FUN=st.err)
    df_aggregated_mean$error<-df_aggregated_error$n
    
    p[[i]]<-ggplot(data=df_aggregated_mean,aes(y=`unlist(df[i])`,x=n, 
                                     color=treatment,fill=treatment,group=treatment))+
      geom_point(stat="identity",position=position_dodge())+
      geom_errorbar(aes(xmin=n-error,xmax=n+error))+
      theme(panel.grid.major = element_blank(), #panel.grid.minor = element_blank(),
            panel.background = element_blank(), axis.line = element_line(colour = "black")) + 
      theme(legend.position = "none") 
    #print(p)
   
   #Generate correlation plot
   ce<-df_aggregated_mean[df_aggregated_mean$treatment=="CORTEXPERIMENTAL",]
   cc<-df_aggregated_mean[df_aggregated_mean$treatment=="CONTROL",]
   g<-ggplot(data=ce,aes(x=ce$n,y=cc$n))+
     geom_point()+
     scale_x_continuous(trans='log10')+
     scale_y_continuous(trans='log10')
   print(g)
  }}
do.call(grid.arrange,p)

df_total_cells<-aggregate(n~uid,data=df,FUN="sum")
colnames(df_total_cells)[2]="total_cells"
df2<-merge(df,df_total_cells,by="uid")
df2$normalized_cell_count<-df2$n/df2$total_cells
df<-df2
df$normalized_cell_count<-df$normalized_cell_count*10000

df_aggregated<-aggregate(normalized_cell_count~uid+treatment+location,data=df,FUN="sum") 

df_aggregated<-aggregate(normalized_cell_count~treatment+location,data=df_aggregated,FUN="mean") 
p<-ggplot(data=df_aggregated,aes(x=n,y=location))+geom_bar(stat="identity")
print(p)

#distribution of the data
p<-ggplot(data=df_aggregated,aes(x=normalized_cell_count,group=uid,color=uid,fill=uid))+geom_density(alpha=0.5)
print(p)


df_aggregated<-aggregate(normalized_cell_count~uid+treatment+location,data=df,FUN="sum") 
df_aggregated_mean<-aggregate(normalized_cell_count~treatment+location,data=df_aggregated,FUN="mean")
df_aggregated_error<-aggregate(normalized_cell_count~treatment+location,data=df_aggregated,FUN=st.err)
df_aggregated_mean$error<-df_aggregated_error$normalized_cell_count

p<-ggplot(data=df_aggregated_mean,aes(x=location,y=normalized_cell_count, 
                                           color=treatment,fill=treatment,group=treatment))+
  geom_point(size=5)+
  geom_point(size=4,fill="white")+
  geom_errorbar(aes(ymin=normalized_cell_count-error,ymax=normalized_cell_count+error))+
  theme(panel.grid.major = element_blank(), #panel.grid.minor = element_blank(),
        panel.background = element_blank(), axis.line = element_line(colour = "black")) + 
  theme(legend.position = "none")+
  theme(axis.text.x=element_text(angle=90,vjust=0.5,hjust=1))
print(p)


#Mediodorsal nucleus of thalamus subset
md<-df[df$location=="Intermediodorsal nucleus of the thalamus" | df$location=="Mediodorsal nucleus of thalamus" |
         df$location=="Mediodorsal nucleus of the thalamus, central part" | df$location=="Mediodorsal nucleus of the thalamus, lateral part" |
         df$location=="Mediodorsal nucleus of the thalamus, medial part",]
md_sum<-aggregate(normalized_cell_count~uid+treatment,data=md,FUN="sum")
md_average<-aggregate(normalized_cell_count~treatment,data=md_sum,FUN="mean")
md_err<-aggregate(normalized_cell_count~treatment,data=md_sum,FUN=st.err)
md_average$error<-md_err$normalized_cell_count

p<-ggplot(data=md_average,aes(x=treatment,y=normalized_cell_count, color=treatment,fill=treatment,group=treatment))+
  geom_point(size=5)+
  geom_point(size=4,fill="white")+
  geom_errorbar(aes(ymin=normalized_cell_count-error,ymax=normalized_cell_count+error))+
  theme(panel.grid.major = element_blank(), #panel.grid.minor = element_blank(),
        panel.background = element_blank(), axis.line = element_line(colour = "black")) + 
  theme(legend.position = "none")+
  theme(axis.text.x=element_text(angle=90,vjust=0.5,hjust=1))
print(p)


#Stats
df_aggregated<-aggregate(normalized_cell_count~uid+treatment+location,data=df,FUN="sum") 
fit<-glmer(normalized_cell_count~location+(1|uid),data=df_aggregated,family=Gamma(link="log"))


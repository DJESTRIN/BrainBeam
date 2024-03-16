cluster_folder=$4
local_folder=$5
ssh_key_path=$1
userid=$2
clustername=$3
#current_dir=$6
rsync -Pav -e 'ssh -i ~/.ssh/thekey.txt' dje4001@cayuga-login1.cac.cornell.edu:$cluster_folder $local_folder && echo "Rsync complete" || $6/foreverdownload.sh $1 $2 $3 $4 $5 $6

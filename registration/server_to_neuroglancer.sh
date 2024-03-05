#!/bin/bash/
# get rid of screens
killall screen

#Passed variables from previous script
cloudreg_directory=$1
echo "This script must be run on cluster's viz node"

# Python script replacing 0 byte files with empty images.
source ~/.bashrc
conda activate cloudreg

init_port=9000
add_num=1

#Loop through samples
for folder in $cloudreg_directory*/
do
	for channel in $folder*/
	do
		if [ -z "$(ls -A $channel)" ]; then
			echo "$channel is empty directory"
		else
			echo "$channel at port number: $init_port"
			screen -dmS $init_port bash -c "echo $channel; exec bash" && screen -r $init_port -p 0 -X stuff "python /home/fs01/dje4001/neuroglancer/cors_webserver.py -d $channel -p $init_port\n"
			init_port=$(($init_port + $add_num))
		fi
	done
done




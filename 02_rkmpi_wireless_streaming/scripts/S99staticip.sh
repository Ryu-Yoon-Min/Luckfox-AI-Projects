#!/bin/sh

MAX_TRIES=30
TRIES=0

check_wifi_ready() {
 if ifconfig wlan0 | grep -q "RUNNING"; then
	return 0
 else
	return 1
 fi
}

static_ip()
{
 killall -9 wpa_supplicant 2>/dev/null
 killall -9 udhcpc 2>/dev/null
 sleep 2

 # <L1> wake up wlan card
 ifconfig wlan0 up
 sleep 2

 # <L2> Connect to AP
 wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant.conf
 sleep 2

 while [ $TRIES -lt $MAX_TRIES ]; do
	if check_wifi_ready; then
		echo "Wi-Fi associated! Setting Static IP now..."
                
                # <L3> Allocated static IP
		ifconfig wlan0 172.30.1.100 netmask 255.255.255.0
		route add default gw 172.30.1.254
		echo "nameserver 8.8.8.8" > /etc/resolv.conf
		
		break
	else
		echo "Waiting for Wi-Fi association..."
		TRIES=$((TRIES + 1))
		sleep 2
	fi
 done
}

case $1 in
	start)
		static_ip &
		;;
	stop)   
                killall wpa_supplicant 2>/dev/null
                ifconfig wlan0 down
		;;
	*)
		exit 1
		;;
esac

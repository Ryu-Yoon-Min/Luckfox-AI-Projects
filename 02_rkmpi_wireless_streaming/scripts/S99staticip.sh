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
 while [ $TRIES -lt $MAX_TRIES ]; do
	if check_wifi_ready; then
		echo "Wi-Fi associated! Setting Static IP now..."

		killall -9 udhcpc 2>/dev/null

		ifconfig wlan0 192.168.1.100 netmask 255.255.255.0
		route add default gw 192.168.1.1
		echo "nameserver 8.8.8.8" > /etc/resolv.conf
		ifconfig wlan0 up

		echo "Static IP set"
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
		;;
	*)
		exit 1
		;;
esac
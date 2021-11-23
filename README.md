# domoticz-venta
Domoticz plugin for venta device (LPH60 WiFi App Control)

### Plugin installation
Either clone this repositorny into Domoticz's python plugin directory

```
$ cd python_dir/config/plugins
$ git clone this_repo_clone_link
```

or simply create directory and copy the plugin.py file into `$ python_dir/config/plugins/domoticz-venta`.
That was an easy part.

### Configuration
Now we need to find out hash for cennection.
It's easiest to sniff packets between your smartphone with [Venta App](https://play.google.com/store/apps/details?id=de.actiworks.ventasimapp&gl=PL) and the device.

#### My process
1. Configure Venta device, and connect it to local network
2. Add you Venta device to Venta App
3. Download and install Wireshark **IMPORTANT NOTICE:** make sure to install `Sshdump` component.
4. Install [PCAP Remote](https://play.google.com/store/apps/details?id=com.egorovandreyrm.pcapremote&gl=PL) on your smartphone
5. Export certificate from PCAP Remote app (Context menu -> Settings -> Export certificate)
6. Start the PCAP Remote server
7. Configure connection in Wireshark (IP, PORT, import certificate)
8. Start Wireshark SSH remote capture
9. Use filter `(ip.dst == ip_of_venta_device or ip.src == ip_of_venta_device) and tcp and data.len > 0`
10. Open Venta App and wait for the communication
11. At his point you can read JSON file in data field but if you want to make it more clear go to step 12.
12. Select any packet with right mouse click and choose follow
13. Read `MacAdress`, `Hash`, `DeviceName` and fill it into python plugin.

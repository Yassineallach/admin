package main

import (
	"fmt"
	"net"
	"net/url"
	"strings"
)

const (
	DiscoveryRequest = "AIRPOINTER?"
	DiscoveryReply   = "AIRPOINTER!"
)

// RunDiscovery answers the phone's UDP broadcast with "AIRPOINTER! <tcp port> <name>".
func RunDiscovery(udpPort, tcpPort int, name string, logf func(string, ...any)) error {
	pc, err := net.ListenPacket("udp4", fmt.Sprintf(":%d", udpPort))
	if err != nil {
		return err
	}
	go func() {
		defer pc.Close()
		buf := make([]byte, 256)
		for {
			n, addr, err := pc.ReadFrom(buf)
			if err != nil {
				return
			}
			if strings.TrimSpace(string(buf[:n])) != DiscoveryRequest {
				continue
			}
			reply := fmt.Sprintf("%s %d %s", DiscoveryReply, tcpPort, url.QueryEscape(name))
			_, _ = pc.WriteTo([]byte(reply), addr)
			logf("Discovery request from %s", addr)
		}
	}()
	return nil
}

//go:build !windows

package main

import (
	"io"
	"net"
)

const defaultMpvPath = "/tmp/mpvsocket"

func dialMpv(path string) (io.ReadWriteCloser, error) { return net.Dial("unix", path) }

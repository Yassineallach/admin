//go:build windows

package main

import (
	"io"
	"os"
)

const defaultMpvPath = `\\.\pipe\mpvsocket`

func dialMpv(path string) (io.ReadWriteCloser, error) {
	return os.OpenFile(path, os.O_RDWR, 0)
}

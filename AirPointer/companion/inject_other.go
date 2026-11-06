//go:build !windows && !linux

package main

import "errors"

func NewInjector() (Injector, error) {
	return nil, errors.New("input injection is implemented for Windows and Linux only")
}

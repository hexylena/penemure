package main

import (
	// "fmt"
	pmm "github.com/hexylena/pm/models"
)

func round() {
	n := pmm.Note{}
	n.ParseNote("projects/7/1/7177e07a-7701-42a5-ae4f-c2c5bc75a974")
	// fmt.Println(n)
	n.SaveNote("out.json")

}

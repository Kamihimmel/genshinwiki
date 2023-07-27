#!/bin/bash

for id in $(cat ../lib/characterlist.json | jq -r ".data[]|select(.spoiler==true)|.id"); do
  echo $id
  python character_ambr.py $id
done

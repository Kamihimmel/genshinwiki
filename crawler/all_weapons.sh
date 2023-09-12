#!/bin/bash

for id in $(cat ../lib/weaponlist.json | jq -r ".data[]|select(.spoiler==true)|.id"); do
  echo $id
  python weapon_ambr.py $id
done

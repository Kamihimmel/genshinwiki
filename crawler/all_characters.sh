#!/usr/bin/zsh

for id in $(cat ../lib/characterlist.json | jq -r ".data[].id"); do
  echo $id
  python character_ambr.py $id
done

cd $1
for f in */*.txt
do
  echo "processing $f"
  sed -i "s/\x0c//g; #" $f
done

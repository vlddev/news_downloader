cd $1
for f in */*.fb2
do
  echo "processing $f"
  sed -i "s/<\.\.\.>/\.\.\./g; s/<…>/…/g; s/\x07//g; s/\x1f//g; s/\x1e//g; s/&ndash;/–/g; s/&mdash;/—/g; s/&rsquo;/\'/g; s/&shy;//g; #" $f
done

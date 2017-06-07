cd "/home/vlad/Downloads/Golos Ukrajiny [Gazeta; Pidshyvka] (1991-2013) [PDF]/Українська мова/$1 рік"
outdir="/home/vlad/Dokumente/python/news_lib/golos_ukr/$1"
echo "outdir $outdir"

mkdir $outdir
for f in *.pdf
do
  echo "processing $f"
  resfile="$outdir/$f"
  resfile=${resfile/pdf/txt}
  echo "resfile $resfile"
  pdftotext "$f" - | iconv -c -t cp1252 | iconv -f cp1251 > "$resfile"
done

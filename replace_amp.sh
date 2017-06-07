cd $1
for f in */*.fb2
do
  echo "processing $f"
  sed -i 's/_/_u/g; # use _ as an escape character. Here escape itself
              s/&\([[:alpha:]][[:alnum:]]*;\)/_a\1/g; # replace & with _a when in entities
              s/&\(#[0-9]\{1,8\};\)/_a\1/g; # &#1234; case
              s/&\(#x[0-9a-fA-F]\{1,8\};\)/_a\1/g; # &#xabcd; case
              s/&/\&amp;/g; # now convert the non-escaped &s
              s/_a/\&/g;s/_u/_/g; # restore escaped & and _' $f
done

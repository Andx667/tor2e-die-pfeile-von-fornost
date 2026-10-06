# make        -> both PDFs in build/
# make sheet  -> only the sheet edition (punched, loose pages)
# make book   -> only the book edition (for binding)
# make maps   -> redraw all maps (tools/maps.py)
# make clean
.PHONY: pdf sheet book maps clean
pdf:
	python3 tools/build.py
sheet book:
	python3 tools/build.py $@
maps:
	python3 tools/maps.py
clean:
	rm -rf build

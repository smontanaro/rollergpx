VENVDIR = ./venv

.PHONY: test
test : virtualenv
	. $(VENVDIR)/bin/activate && bash scripts/test.sh -c

.PHONY: virtualenv
virtualenv : $(VENVDIR)

$(VENVDIR) : rollergpx/rollergpx.py rollergpx/gpxtolatlong.py pyproject.toml
	mkdir -p $(VENVDIR)
	v=`python --version | awk '{print $$2}' | awk -F . '{printf("%2d%02d\n", $$1, $$2)}'` ; \
	if [ $${v} -ge 311 ] ; then \
	  python -m venv $(VENVDIR) ; \
	  . $(VENVDIR)/bin/activate ; \
	  python -m pip install -U pip ; \
	  python -m pip install build pytest pytest-cov ; \
	  python -m build ; \
	  python -m pip install `ls -tr dist/*.whl | tail -1` ; \
	else \
	  echo "Python version $${v} isn't new enough" 1>&2 ; \
	  exit 1 ; \
	fi
	touch $(VENVDIR)

.PHONY : clean
clean : FORCE
	rm -rf venv dist rollergpx.egg-info .coverage .pytest_cache htmlcov

.PHONY : FORCE
FORCE :

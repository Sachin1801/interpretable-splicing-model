git config pull.rebase false

cd /home/ms7490/scratch/code/RNA-splicing-paper/
git pull
cd /home/ms7490/scratch/code/splicing_library_analysis/2021_11_26_figures
cp figs/* /home/ms7490/scratch/code/RNA-splicing-paper/fig
cd /home/ms7490/scratch/code/RNA-splicing-paper/
git add -A .
git commit -m "copying figures"
git push
cd /home/ms7490/scratch/code/splicing_library_analysis/2021_11_26_figures



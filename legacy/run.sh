#!/bin/bash
source /home/AuE/MortralCombat/myenv/bin/activate
cd /home/AuE/MortralCombat  

streamlit run /home/AuE/MortralCombat/MortalCombat.py --server.port 443 \
    --server.sslCertFile /etc/letsencrypt/live/neomortalsurv.net/fullchain.pem \
    --server.sslKeyFile /etc/letsencrypt/live/neomortalsurv.net/privkey.pem



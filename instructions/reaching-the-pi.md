# Reaching the Pi

The Pi answers to **`delia-pi.local`** (mDNS — no IP to remember). Known-good as

## Is it alive?

Run these in order. The first one that fails tells you where the problem is.

```bash
ping -c 3 delia-pi.local                              # 1. on the network?
ssh user@delia-pi.local                          # 2. can I get a shell?
./deploy.sh status                                    # 3. are both services up?
curl -sI http://delia-pi.local:8080 | head -1         # 4. is the web UI serving?
```

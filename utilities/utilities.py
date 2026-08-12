import time
def get_sync_llm_msg(el):
    print("Waiting for LLM response to finish...")
    print(el.count())
    cache_msg=el.inner_text()
    stop_chain=0
    msg=""
   
    while stop_chain<5:
        time.sleep(0.016)
        cache_msg=msg
        msg=el.inner_text()
        msg=msg[msg.find(':')+1:].strip()
        print(f"\r{msg}", end="", flush=True)
        if msg==cache_msg and msg!="":
            stop_chain+=1
        else:
            stop_chain=0
    return msg

      
        
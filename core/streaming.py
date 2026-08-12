import time
import sys

def wait_for_streaming_output(elements):
    while True:
        time.sleep(0.5)
        count=elements.count()
        print(f"count = {count}")
        if count>0:
            element=elements.nth(count-1)
            user_msg_indicator = element.locator('[class~="corner-superellipse/0.98"]')                
            
            if not user_msg_indicator.count()>0:
                return elements.nth(count-1)

def stream_output(el = None):

    """ Prints the live LLM output and returns the response when it is done """
    print("Waiting for LLM response to finish...")
    try:


        print(el.count())


    except:


        print(f"{el} doesn't have method 'count' ! ")



    cache_msg=""

    msg=""

    

    try:
        
        msg=el.inner_text()

    except:

        msg=""

    stop_chain=0
    
    alternator=0

    while stop_chain<60:


        time.sleep(0.016)


        cache_msg=msg

        try:

            msg=el.inner_text()

        except:

            msg=""
        
        msg=msg[msg.find(':')+1:].strip()


        if msg==cache_msg and msg!="":

            
            stop_chain+=1


        elif msg=="":

            alternator= ( alternator+1 ) % 2

            time.sleep(0.016*9)

            if alternator==0:

                msg="\r x"

            else:

                msg="\r +"

            #print(f"\r{msg}",end="",flush=True)
            

        else:

            #rint(f"\r{msg}", end="", flush=True)

            stop_chain=0
        yield msg

   
import sys

last_line_count = 0

import sys

def show_streamed_output(el=None):
    last_msg = ""
    
    for msg in stream_output(el):
        # 1. If current msg is a status symbol ('+' or 'x')
        if msg in ("+", "x"):
            delta = f"\r{msg}"
        
        # 2. If transitioning away from '+' or 'x', overwrite the status character
        elif last_msg in ("+", "x"):
            # \r returns cursor to start; \033[K clears any lingering status character
            delta = f"\r\033[K{msg}"
        
        # 3. Standard text accumulation slice
        else:
            delta = msg[len(last_msg):]
            
        print(delta, end="", flush=True)
        last_msg = msg
        
    print()  # Print a final newline when streaming finishes
    return last_msg
      
def _stream_output():

    with open("input.txt","rt") as f:

        """ Prints the live LLM output and returns the response when it is done """
        print("Waiting for LLM response to finish...")



        cache_msg=""

        msg=""

        

        try:
            
            msg=f.read()


        except:

            msg=""

        stop_chain=0
        
        alternator=0

        while stop_chain<5:


            time.sleep(0.016)


            cache_msg=msg

            try:

                msg=f.read()
                f.seek(0)

            except:

                msg=""
            
            msg=msg[msg.find(':')+1:].strip()


            if msg==cache_msg and msg!="":

                
                stop_chain+=1


            elif msg=="":

                alternator= ( alternator+1 ) % 2

                time.sleep(0.016*9)

                if alternator==0:

                    msg="\r x"

                else:

                    msg="\r +"

                #print(f"\r{msg}",end="",flush=True)
                

            else:

                print(f"\r{msg}", end="", flush=True)

                stop_chain=0
            yield msg

        

        
                
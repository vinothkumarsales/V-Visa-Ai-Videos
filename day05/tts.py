import asyncio, json, edge_tts
s=json.load(open("script.json"))["voiceover_full"]
async def main():
    c=edge_tts.Communicate(s,"en-IN-PrabhatNeural",rate="+12%",boundary="WordBoundary")
    words=[]
    with open("voice.mp3","wb") as f:
        async for ch in c.stream():
            if ch["type"]=="audio": f.write(ch["data"])
            elif ch["type"]=="WordBoundary":
                words.append({"w":ch["text"],"t":ch["offset"]/1e7,"d":ch["duration"]/1e7})
    json.dump(words,open("words.json","w"))
    print(len(words),words[-1])
asyncio.run(main())

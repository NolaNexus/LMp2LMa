"""Auto-graded final exam grader - reads checkpoints/*.json"""
import json, sys, os
CHECKPOINT_DIR = "checkpoints"
def grade(track_id):
    with open(os.path.join(CHECKPOINT_DIR, track_id + ".json")) as f: data=json.load(f)
    return {"track":track_id,"checkpoints":len(data.get("checkpoints",[])),"exam":data.get("final_exam",{}),"status":"READY"}
if __name__=="__main__": import argparse; p=argparse.ArgumentParser(); p.add_argument("track"); print(json.dumps(grade(p.parse_args().track),indent=2))

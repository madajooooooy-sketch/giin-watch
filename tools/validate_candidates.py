#!/usr/bin/env python3
"""Validate candidate list before any human-reviewed publication."""
import argparse,json,sys
from pathlib import Path

def validate(rows,min_house=100):
    errors=[]; seen=set();counts={"衆議院":0,"参議院":0}
    if not isinstance(rows,list):return ["Root must be an array"],counts
    for i,r in enumerate(rows):
        if not isinstance(r,dict):errors.append(f"row {i}: not an object");continue
        house=r.get("house");name=r.get("name");district=r.get("district")
        if house not in counts:errors.append(f"row {i}: invalid house");continue
        if not isinstance(name,str) or not 2<=len(name.strip())<=40:errors.append(f"row {i}: invalid name")
        if not isinstance(district,str) or not district.strip():errors.append(f"row {i}: missing district")
        sources=r.get("sources")
        if not isinstance(sources,list) or not any(isinstance(s,dict) and str(s.get("url","")).startswith("https://") for s in sources):errors.append(f"row {i}: missing HTTPS source")
        key=(house,name,district)
        if key in seen:errors.append(f"row {i}: duplicate {key}")
        seen.add(key);counts[house]+=1
    for house,count in counts.items():
        if count<min_house:errors.append(f"{house}: {count} below review threshold {min_house}")
    return errors,counts

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("file",type=Path);p.add_argument("--min-house",type=int,default=100);a=p.parse_args()
    try: rows=json.loads(a.file.read_text(encoding="utf-8"));errors,counts=validate(rows,a.min_house)
    except Exception as e:print(f"INVALID: {e}");sys.exit(1)
    print(json.dumps({"counts":counts,"valid":not errors,"errors":errors[:50]},ensure_ascii=False,indent=2))
    sys.exit(bool(errors))

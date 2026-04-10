import sys
import os
import clr
import System
import pandas as pd
import traceback

# =====================================================================
# 1. INITIALIZATION & BOILERPLATE
# =====================================================================
# UPDATE THIS PATH TO YOUR DWSIM INSTALLATION FOLDER!
dwsimpath = r"C:\Users\Shivam Sikka\AppData\Local\DWSIM"

if dwsimpath not in sys.path:
    sys.path.append(dwsimpath)

try:
    clr.AddReference(os.path.join(dwsimpath, "DWSIM.Automation.dll"))
    clr.AddReference(os.path.join(dwsimpath, "DWSIM.Interfaces.dll"))
    clr.AddReference(os.path.join(dwsimpath, "DWSIM.Thermodynamics.dll"))
    clr.AddReference(os.path.join(dwsimpath, "DWSIM.UnitOperations.dll"))
except Exception as e:
    print(f"Failed to load DWSIM DLLs. Error: {e}")
    sys.exit(1)

from DWSIM.Automation import Automation3
from DWSIM.Interfaces.Enums.GraphicObjects import ObjectType
from DWSIM.Thermodynamics import PropertyPackages

print("Initializing DWSIM Engine in Headless Mode... (Ignore ThermoC warnings below)")
interf = Automation3()

# =====================================================================
# UTILITY FUNCTIONS (Including the new Enum Bypasser)
# =====================================================================
def get_dwsim_object_code(keyword):
    for val in System.Enum.GetValues(ObjectType):
        if keyword.lower() in val.ToString().lower():
            return val
    raise Exception(f"Could not find object '{keyword}'.")

def get_thermo_class(exact_name):
    dll_path = os.path.join(dwsimpath, "DWSIM.Thermodynamics.dll")
    asm = System.Reflection.Assembly.LoadFrom(dll_path)
    for t in asm.GetExportedTypes():
        if t.IsClass and t.Name.lower() == exact_name.lower():
            return t
    raise Exception(f"CRITICAL: Could not find class '{exact_name}' in Thermodynamics.dll")

def set_enum(obj, prop_name, int_val):
    """Safely converts an integer to the required C# Enum for Python.NET 3.0+"""
    try:
        prop = obj.GetType().GetProperty(prop_name)
        if prop is not None:
            enum_val = System.Enum.ToObject(prop.PropertyType, int_val)
            prop.SetValue(obj, enum_val, None)
    except Exception as e:
        print(f"  [Warning] Could not set enum {prop_name}: {e}")

# Map Objects
MS_CODE = get_dwsim_object_code("material")
ES_CODE = get_dwsim_object_code("energy")
PFR_CODE = get_dwsim_object_code("pfr") 
COL_CODE = get_dwsim_object_code("distillation")

# Map Reactions
ReactionClass = get_thermo_class("Reaction")
ReactionSetClass = get_thermo_class("ReactionSet")

def safe_add_peng_robinson(sim):
    try:
        pr = PropertyPackages.PengRobinsonPropertyPackage()
        sim.AddPropertyPackage(pr)
    except:
        try:
            pr = PropertyPackages.PengRobinsonPropertyPackage(True)
            sim.AddPropertyPackage(pr)
        except:
            sim.CreateAndAddPropertyPackage("Peng-Robinson (PR)")

# =====================================================================
# 2. PART A: PFR SIMULATION FUNCTION
# =====================================================================
def run_pfr(volume, temperature):
    sim = interf.CreateFlowsheet()
    sim.AddCompound("n-Pentane")
    sim.AddCompound("Isopentane")
    
    safe_add_peng_robinson(sim)

    # Create Objects 
    feed_g = sim.AddObject(MS_CODE, 50, 50, "Feed")
    prod_g = sim.AddObject(MS_CODE, 250, 50, "Product")
    energy_g = sim.AddObject(ES_CODE, 150, 100, "Duty")
    pfr_g = sim.AddObject(PFR_CODE, 150, 50, "PFR")

    feed = feed_g.GetAsObject()
    prod = prod_g.GetAsObject()
    energy = energy_g.GetAsObject()
    pfr = pfr_g.GetAsObject()

    # Set Feed Conditions
    feed.SetTemperature(float(temperature))
    feed.SetPressure(101325.0)
    feed.SetMolarFlow(100.0)
    
    comp = System.Array.CreateInstance(System.Double, 2)
    comp[0] = 1.0
    comp[1] = 0.0
    feed.SetOverallComposition(comp)

    # Instantiate Reaction safely
    reac = System.Activator.CreateInstance(ReactionClass)
    set_enum(reac, "ReactionType", 1)  # 1 = Kinetic
    reac.Name = "Isomerization"
    reac.Description = "n-Pentane to Isopentane"

    # Add compounds using Components
    rsb_reactant = System.Activator.CreateInstance(get_thermo_class("ReactionStoichBase"), "n-Pentane", -1.0, False, 0.0, 0.0)
    rsb_product = System.Activator.CreateInstance(get_thermo_class("ReactionStoichBase"), "Isopentane", 1.0, True, 0.0, 0.0)
    reac.Components.Add("n-Pentane", rsb_reactant)
    reac.Components.Add("Isopentane", rsb_product)

    reac.A_Forward = 10000.0  
    reac.E_Forward = 50000.0  
    reac.BaseCompound = "n-Pentane"
    
    # Safe Enum assignments
    set_enum(reac, "Basis", 0)
    set_enum(reac, "Phase", 1)

    sim.AddReaction(reac)
    
    rset = System.Activator.CreateInstance(ReactionSetClass)
    rset.Name = "IsoSet"
    rset.Description = "Isomerization Set"
    sim.AddReactionSet(rset)

    # Connect
    sim.ConnectObjects(feed_g.GraphicObject, pfr_g.GraphicObject, -1, -1)
    sim.ConnectObjects(pfr_g.GraphicObject, prod_g.GraphicObject, -1, -1)
    sim.ConnectObjects(energy_g.GraphicObject, pfr_g.GraphicObject, -1, -1)

    pfr.ReactionSet = rset.ID
    pfr.Volume = float(volume)
    pfr.Temperature = float(temperature)
    
    # Safe Enum assignment for PFR Operation Mode
    set_enum(pfr, "OperationMode", 1) # 1 = Isothermal

    sim.RequestCalculation()

    in_nC5 = feed.GetCompoundMolarFlow("n-Pentane")
    out_nC5 = prod.GetCompoundMolarFlow("n-Pentane")
    conversion = ((in_nC5 - out_nC5) / in_nC5) * 100.0 if in_nC5 > 0 else 0.0

    return {
        "Type": "PFR", "PFR_Volume_m3": volume, "PFR_FeedTemp_K": temperature,
        "Col_Stages": None, "Col_Reflux": None,
        "Conversion_%": conversion, "nC5_Out_mol_s": out_nC5,
        "iC5_Out_mol_s": prod.GetCompoundMolarFlow("Isopentane"),
        "Heat_Duty_kW": energy.GetEnergyFlow(),
        "Outlet_Temp_K": prod.GetTemperature(),
        "Col_nC5_Purity_%": None, "Col_iC5_Purity_%": None,
        "Condenser_Duty_kW": None, "Reboiler_Duty_kW": None
    }

# =====================================================================
# 3. PART B: DISTILLATION COLUMN SIMULATION FUNCTION
# =====================================================================
def run_column(stages, reflux_ratio):
    sim = interf.CreateFlowsheet()
    sim.AddCompound("n-Pentane")
    sim.AddCompound("Isopentane")
    
    safe_add_peng_robinson(sim)

    # Create Feed
    feed_g = sim.AddObject(MS_CODE, 50, 150, "Feed")
    feed = feed_g.GetAsObject()
    feed.SetTemperature(320.0)
    feed.SetPressure(101325.0)
    feed.SetMolarFlow(100.0)
    
    comp = System.Array.CreateInstance(System.Double, 2)
    comp[0] = 0.5
    comp[1] = 0.5
    feed.SetOverallComposition(comp)

    # Create Column
    dist_g = sim.AddObject(MS_CODE, 250, 50, "Distillate")
    bot_g = sim.AddObject(MS_CODE, 250, 250, "Bottoms")
    col_g = sim.AddObject(COL_CODE, 150, 150, "Column")
    
    col = col_g.GetAsObject()
    dist = dist_g.GetAsObject()
    bot = bot_g.GetAsObject()

    # Connect
    sim.ConnectObjects(feed_g.GraphicObject, col_g.GraphicObject, -1, -1)
    sim.ConnectObjects(col_g.GraphicObject, dist_g.GraphicObject, -1, -1)
    sim.ConnectObjects(col_g.GraphicObject, bot_g.GraphicObject, -1, -1)

    col.NumberOfStages = int(stages)
    
    # Modern Column Specification Assignments
    col.CondenserSpecValue = float(reflux_ratio) 
    col.ReboilerSpecValue = 50.0 

    sim.RequestCalculation()

    dist_comp = dist.GetPhase("Overall").Compounds
    bot_comp = bot.GetPhase("Overall").Compounds

    cond_val, reb_val = 0.0, 0.0
    try:
        cond_val = col.CondenserHeatLoad
        reb_val = col.ReboilerHeatLoad
    except:
        pass

    return {
        "Type": "Column", "PFR_Volume_m3": None, "PFR_FeedTemp_K": None,
        "Col_Stages": stages, "Col_Reflux": reflux_ratio,
        "Conversion_%": None, "nC5_Out_mol_s": None, "iC5_Out_mol_s": None,
        "Heat_Duty_kW": None, "Outlet_Temp_K": None,
        "Col_nC5_Purity_%": bot_comp["n-Pentane"].MoleFraction * 100,
        "Col_iC5_Purity_%": dist_comp["Isopentane"].MoleFraction * 100,
        "Condenser_Duty_kW": cond_val,
        "Reboiler_Duty_kW": reb_val
    }

# =====================================================================
# 4. PART C: PARAMETRIC SWEEP AND LOGGING
# =====================================================================
if __name__ == "__main__":
    print("--- STARTING PARAMETRIC SWEEPS ---")
    all_results = []

    vols_to_test = [2.0, 5.0, 10.0]
    temps_to_test = [340.0, 350.0, 360.0]

    for v in vols_to_test:
        for t in temps_to_test:
            print(f"Running PFR -> Vol: {v} m3 | Temp: {t} K")
            try:
                res = run_pfr(v, t)
                res["Status"] = "Success"
                res["Error_Message"] = ""
                all_results.append(res)
                print("  -> Success!")
            except Exception as e:
                error_trace = traceback.format_exc().splitlines()[-1]
                print(f"  -> FAILED: {error_trace}")
                all_results.append({
                    "Type": "PFR", "PFR_Volume_m3": v, "PFR_FeedTemp_K": t, 
                    "Status": "Failed", "Error_Message": error_trace
                })

    stages_to_test = [10, 15, 20]
    reflux_to_test = [1.5, 2.0, 2.5]

    for s in stages_to_test:
        for r in reflux_to_test:
            print(f"Running Column -> Stages: {s} | Reflux: {r}")
            try:
                res = run_column(s, r)
                res["Status"] = "Success"
                res["Error_Message"] = ""
                all_results.append(res)
                print("  -> Success!")
            except Exception as e:
                error_trace = traceback.format_exc().splitlines()[-1]
                print(f"  -> FAILED: {error_trace}")
                all_results.append({
                    "Type": "Column", "Col_Stages": s, "Col_Reflux": r,
                    "Status": "Failed", "Error_Message": error_trace
                })

    print("\nSaving results to results.csv...")
    df = pd.DataFrame(all_results)
    
    cols = [
        "Type", "Status", "Error_Message", 
        "PFR_Volume_m3", "PFR_FeedTemp_K", "Col_Stages", "Col_Reflux",
        "Conversion_%", "nC5_Out_mol_s", "iC5_Out_mol_s", "Heat_Duty_kW", "Outlet_Temp_K",
        "Col_nC5_Purity_%", "Col_iC5_Purity_%", "Condenser_Duty_kW", "Reboiler_Duty_kW"
    ]
    df = df.reindex(columns=cols)
    df.to_csv("results.csv", index=False)
    print("Task Complete! Check results.csv for the data.")
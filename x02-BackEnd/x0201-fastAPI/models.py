from sqlalchemy import Column, Integer, String, Enum, TIMESTAMP, text, DateTime, JSON, Float, ForeignKey, Date, Boolean, func
from sqlalchemy.orm import relationship
from database import Base
import enum

# Enums
class UserRole(str, enum.Enum):
    Admin = "Admin"
    Manager = "Manager"
    Operator = "Operator"
    QC_Inspector = "QC Inspector"
    Viewer = "Viewer"
    
class UserStatus(str, enum.Enum):
    Active = "Active"
    Inactive = "Inactive"

# User Model
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(Enum(UserRole), default=UserRole.Operator)
    department = Column(String(100))
    status = Column(Enum(UserStatus), default=UserStatus.Active)
    permissions = Column(JSON)
    last_login = Column(DateTime)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), onupdate=func.now())

# Ingredient Model
class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    blind_code = Column(String(50), index=True)
    mat_sap_code = Column(String(50), index=True, nullable=True)
    re_code = Column(String(50)) # Re-Code
    ingredient_id = Column(String(50), nullable=False, index=True) # Ingredient code (not unique)
    name = Column(String(150), nullable=False)
    unit = Column(String(20), default="kg")
    Group = Column(String(50))  # Colour, Flavor, etc.
    std_package_size = Column(Float, default=25.0) # Added standard package size
    std_prebatch_batch_size = Column(Float, default=0.0) # Added standard prebatch batch size
    status = Column(String(20), default="Active")  # Active, Inactive
    creat_by = Column(String(50), nullable=False)  # Username who created
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    update_by = Column(String(50))  # Username who last updated
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), onupdate=func.now())

# Ingredient Intake List Model (formerly Ingredient Receive History / Ingredient Receipt)
class IngredientIntakeList(Base):
    __tablename__ = "ingredient_intake_lists"

    id = Column(Integer, primary_key=True, index=True)
    intake_lot_id = Column(String(50), nullable=False, index=True)
    lot_id = Column(String(50), nullable=False)
    warehouse_location = Column(String(50))
    blind_code = Column(String(50), index=True)
    mat_sap_code = Column(String(50), nullable=False, index=True)
    re_code = Column(String(50))
    material_description = Column(String(200)) # Merged from Receipt
    uom = Column(String(20)) # Merged from Receipt
    intake_vol = Column(Float, nullable=False)
    remain_vol = Column(Float, nullable=False)
    intake_package_vol = Column(Float)
    package_intake = Column(Integer)
    expire_date = Column(DateTime)
    status = Column(String(20), default="Active")
    intake_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    intake_by = Column(String(50), nullable=False)
    edit_by = Column(String(50))
    edit_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), onupdate=func.now())
    
    # New fields
    po_number = Column(String(50))
    manufacturing_date = Column(DateTime)
    batch_prepare_vol = Column(Float) # Merged from Receipt
    std_package_size = Column(Float, default=25.0) # Merged from Receipt

    # Relationship to history
    history = relationship("IngredientIntakeHistory", back_populates="intake_record", cascade="all, delete-orphan")

# Ingredient Intake History Model
class IngredientIntakeHistory(Base):
    __tablename__ = "ingredient_intake_history"

    id = Column(Integer, primary_key=True, index=True)
    intake_list_id = Column(Integer, ForeignKey("ingredient_intake_lists.id"), nullable=False)
    action = Column(String(50), nullable=False) # e.g. "Status Change", "Created", "Modified"
    old_status = Column(String(20))
    new_status = Column(String(20))
    remarks = Column(String(255))
    changed_by = Column(String(50), nullable=False)
    changed_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

    # Relationship back to the main intake record
    intake_record = relationship("IngredientIntakeList", back_populates="history")

# Sku Model (formerly Recipe)
class Sku(Base):
    __tablename__ = "sku_masters"

    id = Column(Integer, primary_key=True, index=True)
    sku_id = Column(String(50), unique=True, nullable=False, index=True)
    sku_name = Column(String(200), nullable=False)
    std_batch_size = Column(Float)
    uom = Column(String(20))
    status = Column(String(20), default="Active")
    creat_by = Column(String(50), nullable=False)
    update_by = Column(String(50))
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), onupdate=func.now())

    # Relationship to steps
    steps = relationship("SkuStep", back_populates="sku", foreign_keys="[SkuStep.sku_id]", primaryjoin="Sku.sku_id == SkuStep.sku_id")

class SkuStep(Base):
    __tablename__ = "sku_steps"

    id = Column(Integer, primary_key=True, index=True)
    sku_id = Column(String(50), ForeignKey("sku_masters.sku_id"), index=True, nullable=True)
    phase_number = Column(String(20), index=True, nullable=True) # Added index
    phase_id = Column(String(50), index=True, nullable=True) # Added index
    master_step = Column(Boolean, default=False)
    sub_step = Column(Integer, nullable=False)
    action = Column(String(100))
    re_code = Column(String(50))
    action_code = Column(String(50))
    setup_step = Column(String(100)) # Store as string or JSON
    destination = Column(String(100))
    require = Column(Float)
    uom = Column(String(20)) # Added UOM
    low_tol = Column(Float)
    high_tol = Column(Float)
    step_condition = Column(String(100)) # Renamed from condition to avoid reserved word
    agitator_rpm = Column(Float)
    high_shear_rpm = Column(Float)
    temperature = Column(Float)
    temp_low = Column(Float) # Temperature Offset Low / Min
    temp_high = Column(Float) # Temperature Offset High / Max
    step_time = Column(Integer) # Seconds
    step_timer_control = Column(Integer) # 0 or 1
    
    # Flags from image
    qc_temp = Column(Boolean, default=False)
    record_steam_pressure = Column(Boolean, default=False)
    record_ctw = Column(Boolean, default=False)
    operation_brix_record = Column(Boolean, default=False)
    operation_ph_record = Column(Boolean, default=False)
    
    # Setpoints
    brix_sp = Column(String(50))
    ph_sp = Column(String(50))

    action_description = Column(String(200)) # Added specific action description
    
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), onupdate=func.now())

    sku = relationship("Sku", back_populates="steps", foreign_keys=[sku_id], primaryjoin="Sku.sku_id == SkuStep.sku_id")

# Production Plan Model
class ProductionPlanHistory(Base):
    __tablename__ = "production_plan_history"

    id = Column(Integer, primary_key=True, index=True)
    plan_db_id = Column(Integer, ForeignKey("production_plans.id"), nullable=False)
    action = Column(String(50), nullable=False)  # e.g., 'cancel', 'create', 'update'
    old_status = Column(String(20))
    new_status = Column(String(20))
    remarks = Column(String(255))
    changed_by = Column(String(50), nullable=False)
    changed_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

    plan = relationship("ProductionPlan", backref="history")

class ProductionPlan(Base):
    __tablename__ = "production_plans"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(String(50), unique=True, nullable=False, index=True)
    sku_id = Column(String(50), nullable=False)
    sku_name = Column(String(200))
    plant = Column(String(50))  # Mixing 1, 2, 3
    total_volume = Column(Float)
    total_plan_volume = Column(Float)
    batch_size = Column(Float)
    num_batches = Column(Integer)
    start_date = Column(Date)
    finish_date = Column(Date)
    status = Column(String(20), default="Planned")
    # Status flags
    flavour_house = Column(Boolean, default=False)
    spp = Column(Boolean, default=False)
    batch_prepare = Column(Boolean, default=False)
    ready_to_product = Column(Boolean, default=False)
    production = Column(Boolean, default=False)
    done = Column(Boolean, default=False)
    # User tracking
    created_by = Column(String(50))
    updated_by = Column(String(50))
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), onupdate=func.now())

    batches = relationship("ProductionBatch", back_populates="plan", cascade="all, delete-orphan")

class ProductionBatch(Base):
    __tablename__ = "production_batches"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("production_plans.id"), nullable=False)
    batch_id = Column(String(100), unique=True, nullable=False, index=True) # e.g. 2025-11-12-01001
    sku_id = Column(String(50), nullable=False)
    plant = Column(String(50))
    batch_size = Column(Float)
    status = Column(String(50), default="Created")
    # Status flags
    flavour_house = Column(Boolean, default=False)
    spp = Column(Boolean, default=False)
    batch_prepare = Column(Boolean, default=False)
    ready_to_product = Column(Boolean, default=False)
    production = Column(Boolean, default=False)
    done = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), onupdate=func.now())

    plan = relationship("ProductionPlan", back_populates="batches")

class PreBatchReq(Base):
    __tablename__ = "prebatch_reqs"

    id = Column(Integer, primary_key=True, index=True)
    batch_db_id = Column(Integer, ForeignKey("production_batches.id"), nullable=False)
    plan_id = Column(String(50), index=True)
    batch_id = Column(String(100), index=True)
    re_code = Column(String(50), index=True)
    ingredient_name = Column(String(200))
    required_volume = Column(Float)
    wh = Column(String(50)) # warehouse location
    status = Column(Integer, default=0) # 0=Pending, 1=In-Progress, 2=Completed
    
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), onupdate=func.now())

    batch = relationship("ProductionBatch", backref="reqs")

class PreBatchRec(Base):
    __tablename__ = "prebatch_recs"

    id = Column(Integer, primary_key=True, index=True)
    req_id = Column(Integer, ForeignKey("prebatch_reqs.id"), nullable=True)
    batch_record_id = Column(String(100), unique=True, nullable=False, index=True)
    plan_id = Column(String(50), index=True)
    re_code = Column(String(50), index=True)
    package_no = Column(Integer)
    total_packages = Column(Integer)
    net_volume = Column(Float)
    total_volume = Column(Float)
    total_request_volume = Column(Float)
    intake_lot_id = Column(String(50), index=True)
    mat_sap_code = Column(String(50), index=True)
    prebatch_id = Column(String(100), index=True)
    recode_batch_id = Column(String(50), index=True)
    
    # Re-check fields
    recheck_status = Column(Integer, default=0) # 0=Pending, 1=OK, 2=Error
    recheck_at = Column(TIMESTAMP, nullable=True)
    recheck_by = Column(String(50), nullable=True)
    
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

    req = relationship("PreBatchReq", backref="recs")

class SkuAction(Base):
    __tablename__ = "sku_actions"

    action_code = Column(String(50), primary_key=True)
    action_description = Column(String(200), nullable=False)
    component_filter = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), onupdate=func.now())

class SkuPhase(Base):
    __tablename__ = "sku_phases"

    phase_id = Column(Integer, primary_key=True)  # e.g., 10, 20, 30
    phase_code = Column(String(50), nullable=True) # e.g., "B001"
    phase_description = Column(String(200), nullable=False)  # e.g., "Mixing", "Heating", "Cooling"
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), onupdate=func.now())

class SkuDestination(Base):
    __tablename__ = "sku_destinations"

    id = Column(Integer, primary_key=True, index=True)
    destination_code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(200))

# Plant Model
class Plant(Base):
    __tablename__ = "plants"

    id = Column(Integer, primary_key=True, index=True)
    plant_id = Column(String(50), unique=True, nullable=False, index=True)
    plant_name = Column(String(100), nullable=False)
    plant_capacity = Column(Float, default=0)
    plant_description = Column(String(255))
    status = Column(String(20), default="Active")
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), onupdate=func.now())

# Warehouse Model
class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    status = Column(String(20), default="Active")
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), onupdate=func.now())

# ============================================================================
# DATABASE VIEWS (Read-Only Models)
# ============================================================================

class VSkuMasterDetail(Base):
    """View: SKU Master with step counts and metadata"""
    __tablename__ = "v_sku_master_detail"
    __table_args__ = {'info': {'is_view': True}}
    
    id = Column(Integer, primary_key=True)
    sku_id = Column(String(50))
    sku_name = Column(String(200))
    std_batch_size = Column(Float)
    uom = Column(String(20))
    status = Column(String(20))
    creat_by = Column(String(50))
    created_at = Column(TIMESTAMP)
    update_by = Column(String(50))
    updated_at = Column(TIMESTAMP)
    total_phases = Column(Integer)
    total_sub_steps = Column(Integer)
    last_step_update = Column(TIMESTAMP)


class VSkuStepDetail(Base):
    """View: SKU Steps with all lookups and computed fields"""
    __tablename__ = "v_sku_step_detail"
    __table_args__ = {'info': {'is_view': True}}
    
    step_id = Column("step_id", Integer, primary_key=True) # Matches view alias
    sku_id = Column(String(50))
    phase_number = Column(String(20))
    phase_id = Column(String(50))
    sub_step = Column(Integer)
    action = Column(String(100))
    re_code = Column(String(50))
    action_code = Column(String(50))
    setup_step = Column(String(100))
    destination = Column(String(100))
    require = Column(Float)
    uom = Column(String(20))
    low_tol = Column(Float)
    high_tol = Column(Float)
    step_condition = Column(String(100))
    agitator_rpm = Column(Float)
    high_shear_rpm = Column(Float)
    temperature = Column(Float)
    temp_low = Column(Float)
    temp_high = Column(Float)
    step_time = Column(Integer)
    step_timer_control = Column(Integer)
    
    ph = Column(Float, nullable=True)
    brix = Column(Float, nullable=True)
    
    qc_temp = Column(Boolean)
    record_steam_pressure = Column(Boolean)
    record_ctw = Column(Boolean)
    operation_brix_record = Column(Boolean)
    operation_ph_record = Column(Boolean)
    brix_sp = Column(String(50))
    ph_sp = Column(String(50))
    
    step_created_at = Column(TIMESTAMP)
    step_updated_at = Column(TIMESTAMP)
    
    # SKU Master info
    sku_name = Column(String(200))
    std_batch_size = Column(Float)
    uom_master = Column(String(20)) # Renamed to avoid collision or clarify
    sku_status = Column(String(20))
    
    # Lookups
    action_description = Column(String(200)) # Matches view column name

    destination_description = Column(String(200))
    ingredient_name = Column(String(200))
    mat_sap_code = Column(String(50))
    blind_code = Column(String(50))
    ingredient_category = Column(String(100))
    ingredient_unit = Column(String(20))
    std_package_size = Column(Float)
    
    # Computed fields
    step_label = Column(String(20))
    full_action_description = Column(String(300))
    full_destination_description = Column(String(300))


class VSkuComplete(Base):
    """View: Complete denormalized SKU data for export/reporting"""
    __tablename__ = "v_sku_complete"
    __table_args__ = {'info': {'is_view': True}}
    
    # Composite primary key workaround - use sku_id + step_number
    sku_id = Column(String(50), primary_key=True)
    step_number = Column(String(20), primary_key=True)
    
    sku_name = Column(String(200))
    std_batch_size = Column(Float)
    uom = Column(String(20))
    status = Column(String(20))
    
    phase_number = Column(String(20))
    phase_id = Column(String(50))
    sub_step = Column(Integer)
    
    action = Column(String(100))
    action_code = Column(String(50))
    action_description = Column(String(200))
    
    re_code = Column(String(50))
    ingredient_name = Column(String(200))
    mat_sap_code = Column(String(50))
    blind_code = Column(String(50))
    
    destination = Column(String(100))
    destination_description = Column(String(200))
    
    required_amount = Column(Float)
    low_tol = Column(Float)
    high_tol = Column(Float)
    agitator_rpm = Column(Float)
    high_shear_rpm = Column(Float)
    temperature = Column(Float)
    step_time = Column(Integer)
    
    setup_step = Column(String(100))
    
    creat_by = Column(String(50))
    created_at = Column(TIMESTAMP)
    update_by = Column(String(50))
    updated_at = Column(TIMESTAMP)




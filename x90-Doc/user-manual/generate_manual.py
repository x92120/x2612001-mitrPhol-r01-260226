#!/usr/bin/env python3
"""Generate bilingual (EN/TH) HTML user manual for xMixing application."""
import base64, os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SS_DIR = os.path.join(SCRIPT_DIR, "screenshots")

def img_to_base64(filename):
    path = os.path.join(SS_DIR, filename)
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def img_tag(filename, alt="Screenshot"):
    b64 = img_to_base64(filename)
    if not b64:
        return f'<div class="no-img">[Image: {filename}]</div>'
    return f'<img src="data:image/png;base64,{b64}" alt="{alt}" class="screenshot">'

# ─── Chapter Data ───
chapters = [
    {
        "num": "1",
        "en_title": "Login",
        "th_title": "เข้าสู่ระบบ",
        "img": "00-login.png",
        "en_content": """
<p>Open the application in a web browser. You will see the <strong>Login Page</strong>.</p>
<h4>Steps / ขั้นตอน:</h4>
<ol>
  <li>Enter your <strong>Username</strong> in the username field.</li>
  <li>Enter your <strong>Password</strong> in the password field.</li>
  <li>Click the <strong>"Login"</strong> button.</li>
  <li>If successful, you will be redirected to the <strong>Dashboard</strong>.</li>
</ol>
<div class="tip"><strong>💡 Tip:</strong> If you don't have an account, click "Register here" to create one.</div>
""",
        "th_content": """
<p>เปิดแอปพลิเคชันในเว็บเบราว์เซอร์ คุณจะเห็น <strong>หน้าเข้าสู่ระบบ</strong></p>
<h4>ขั้นตอน:</h4>
<ol>
  <li>กรอก <strong>ชื่อผู้ใช้</strong> ในช่องชื่อผู้ใช้</li>
  <li>กรอก <strong>รหัสผ่าน</strong> ในช่องรหัสผ่าน</li>
  <li>คลิกปุ่ม <strong>"เข้าสู่ระบบ"</strong></li>
  <li>หากสำเร็จ ระบบจะนำคุณไปยัง <strong>แดชบอร์ด</strong></li>
</ol>
<div class="tip"><strong>💡 เคล็ดลับ:</strong> หากยังไม่มีบัญชี ให้คลิก "ลงทะเบียนที่นี่" เพื่อสร้างบัญชีใหม่</div>
""",
    },
    {
        "num": "2",
        "en_title": "Dashboard",
        "th_title": "แดชบอร์ด",
        "img": "01-dashboard.png",
        "en_content": """
<p>The <strong>Dashboard</strong> is the main landing page after login. It provides an overview of the system status.</p>
<h4>Key Elements:</h4>
<ul>
  <li><strong>Welcome Banner</strong> — Shows your username, role, and account status.</li>
  <li><strong>Statistics Cards</strong> — Displays Total SKUs, Ingredients Stock, Pending Batches, and Active Productions.</li>
  <li><strong>Quick Access Buttons</strong> — Shortcuts to Create SKU, Ingredient Intake, Plan Batch, and Start Production.</li>
  <li><strong>Recent Activities</strong> — Timeline of recent system events and batch updates.</li>
</ul>
<div class="tip"><strong>💡 Tip:</strong> Use the <strong>Quick Access</strong> buttons to navigate directly to the most common tasks.</div>
""",
        "th_content": """
<p><strong>แดชบอร์ด</strong> เป็นหน้าหลักหลังจากเข้าสู่ระบบ แสดงภาพรวมสถานะของระบบ</p>
<h4>องค์ประกอบหลัก:</h4>
<ul>
  <li><strong>แบนเนอร์ต้อนรับ</strong> — แสดงชื่อผู้ใช้ บทบาท และสถานะบัญชี</li>
  <li><strong>การ์ดสถิติ</strong> — แสดง SKU ทั้งหมด, สต็อกวัตถุดิบ, แบตช์ที่รอดำเนินการ, และการผลิตที่กำลังดำเนินอยู่</li>
  <li><strong>ปุ่มทางลัด</strong> — ลัดไปยังสร้าง SKU, รับวัตถุดิบ, วางแผนแบตช์, และเริ่มการผลิต</li>
  <li><strong>กิจกรรมล่าสุด</strong> — ไทม์ไลน์เหตุการณ์ล่าสุดในระบบ</li>
</ul>
<div class="tip"><strong>💡 เคล็ดลับ:</strong> ใช้ปุ่ม <strong>ทางลัด</strong> เพื่อนำทางไปยังงานที่ใช้บ่อยที่สุดโดยตรง</div>
""",
    },
    {
        "num": "3",
        "en_title": "Ingredient Intake",
        "th_title": "รับวัตถุดิบ",
        "img": "02-ingredient-intake.png",
        "en_content": """
<p>The <strong>Ingredient Intake</strong> page is used to log incoming raw materials into the system.</p>
<h4>Steps to Record an Intake:</h4>
<ol>
  <li><strong>Scan or type the Ingredient Code</strong> — The system auto-fills MAT.SAP Code, Re-Code, and Ingredient Name.</li>
  <li>Select the <strong>Intake Warehouse Location</strong> from the dropdown.</li>
  <li>Enter the <strong>Lot Number</strong> and optionally a <strong>PO Number</strong>.</li>
  <li>Set <strong>Manufacturing Date</strong> and <strong>Expire Date</strong>.</li>
  <li>Enter <strong>Intake Volume (kg)</strong> and <strong>Package Volume (kg)</strong>. The number of packages is auto-calculated.</li>
  <li>Click <strong>"Save Intake"</strong> to record the entry.</li>
</ol>
<h4>Intake List Table:</h4>
<p>Below the form, the <strong>Ingredient Intake List</strong> shows all recorded intakes with columns for ID, Lot ID, Warehouse, MAT.SAP Code, Description, Volume, and Expire Date. Use the toolbar icons to refresh, filter, or export data.</p>
""",
        "th_content": """
<p>หน้า <strong>รับวัตถุดิบ</strong> ใช้สำหรับบันทึกวัตถุดิบที่เข้ามาในระบบ</p>
<h4>ขั้นตอนการบันทึกการรับ:</h4>
<ol>
  <li><strong>สแกนหรือพิมพ์รหัสวัตถุดิบ</strong> — ระบบจะกรอก MAT.SAP Code, Re-Code, และชื่อวัตถุดิบอัตโนมัติ</li>
  <li>เลือก <strong>สถานที่รับ (คลังสินค้า)</strong> จากเมนูดรอปดาวน์</li>
  <li>กรอก <strong>หมายเลข Lot</strong> และ <strong>หมายเลข PO</strong> (ถ้ามี)</li>
  <li>ตั้ง <strong>วันที่ผลิต</strong> และ <strong>วันหมดอายุ</strong></li>
  <li>กรอก <strong>ปริมาณรับ (กก.)</strong> และ <strong>ปริมาณต่อถุง (กก.)</strong> จำนวนถุงจะคำนวณอัตโนมัติ</li>
  <li>คลิก <strong>"บันทึกการรับ"</strong> เพื่อบันทึกรายการ</li>
</ol>
<h4>ตารางรายการรับ:</h4>
<p>ด้านล่างแบบฟอร์ม <strong>รายการรับวัตถุดิบ</strong> แสดงรายการทั้งหมดพร้อมคอลัมน์ ID, Lot ID, คลังสินค้า, MAT.SAP Code, คำอธิบาย, ปริมาณ, และวันหมดอายุ ใช้ไอคอนแถบเครื่องมือเพื่อรีเฟรช กรอง หรือส่งออกข้อมูล</p>
""",
    },
    {
        "num": "4",
        "en_title": "Ingredient Configuration",
        "th_title": "ตั้งค่าวัตถุดิบ",
        "img": "03-ingredient-config.png",
        "en_content": """
<p>Manage the <strong>master list of ingredients</strong> used across the system.</p>
<h4>Features:</h4>
<ul>
  <li><strong>View</strong> all ingredients in a searchable, sortable table.</li>
  <li><strong>Add New Ingredient</strong> — Click the "+" button to open the creation dialog. Fill in Ingredient ID, Name, MAT.SAP Code, Re-Code, Description, and Unit of Measure.</li>
  <li><strong>Edit</strong> — Click the edit icon on any row to modify ingredient details.</li>
  <li><strong>Delete</strong> — Click the delete icon to remove an ingredient (requires confirmation).</li>
  <li><strong>Print Labels</strong> — Generate and print barcode labels for ingredients.</li>
</ul>
""",
        "th_content": """
<p>จัดการ <strong>รายการหลักของวัตถุดิบ</strong> ที่ใช้ทั่วทั้งระบบ</p>
<h4>คุณสมบัติ:</h4>
<ul>
  <li><strong>ดู</strong> วัตถุดิบทั้งหมดในตารางที่ค้นหาและเรียงลำดับได้</li>
  <li><strong>เพิ่มวัตถุดิบใหม่</strong> — คลิกปุ่ม "+" เพื่อเปิดกล่องสร้าง กรอก ID วัตถุดิบ, ชื่อ, MAT.SAP Code, Re-Code, คำอธิบาย, และหน่วยวัด</li>
  <li><strong>แก้ไข</strong> — คลิกไอคอนแก้ไขในแถวเพื่อแก้ไขรายละเอียด</li>
  <li><strong>ลบ</strong> — คลิกไอคอนลบเพื่อลบวัตถุดิบ (ต้องยืนยัน)</li>
  <li><strong>พิมพ์ฉลาก</strong> — สร้างและพิมพ์ฉลากบาร์โค้ดสำหรับวัตถุดิบ</li>
</ul>
""",
    },
    {
        "num": "5",
        "en_title": "SKU Management",
        "th_title": "จัดการ SKU",
        "img": "04-sku.png",
        "en_content": """
<p>The <strong>SKU Management</strong> page allows you to create and manage product recipes (SKUs).</p>
<h4>Features:</h4>
<ul>
  <li><strong>SKU List</strong> — View all existing SKUs with their details.</li>
  <li><strong>Create New SKU</strong> — Define a new product with SKU ID, Name, Batch Size (kg), and Plant assignment.</li>
  <li><strong>Recipe Builder</strong> — Add ingredients to an SKU with specific percentages or weights. The system calculates exact volumes based on batch size.</li>
  <li><strong>Package Configuration</strong> — Define package types and sizes for each SKU.</li>
  <li><strong>Edit / Delete</strong> — Modify or remove existing SKUs.</li>
</ul>
<div class="tip"><strong>💡 Tip:</strong> Ensure ingredient percentages total 100% for accurate batch calculations.</div>
""",
        "th_content": """
<p>หน้า <strong>จัดการ SKU</strong> ให้คุณสร้างและจัดการสูตรผลิตภัณฑ์ (SKU)</p>
<h4>คุณสมบัติ:</h4>
<ul>
  <li><strong>รายการ SKU</strong> — ดู SKU ทั้งหมดพร้อมรายละเอียด</li>
  <li><strong>สร้าง SKU ใหม่</strong> — กำหนดผลิตภัณฑ์ใหม่ด้วย SKU ID, ชื่อ, ขนาดแบตช์ (กก.), และโรงงาน</li>
  <li><strong>ตัวสร้างสูตร</strong> — เพิ่มวัตถุดิบใน SKU พร้อมเปอร์เซ็นต์หรือน้ำหนักเฉพาะ ระบบจะคำนวณปริมาณที่แน่นอนตามขนาดแบตช์</li>
  <li><strong>การตั้งค่าบรรจุภัณฑ์</strong> — กำหนดประเภทและขนาดบรรจุภัณฑ์สำหรับแต่ละ SKU</li>
  <li><strong>แก้ไข / ลบ</strong> — แก้ไขหรือลบ SKU ที่มีอยู่</li>
</ul>
<div class="tip"><strong>💡 เคล็ดลับ:</strong> ตรวจสอบให้แน่ใจว่าเปอร์เซ็นต์วัตถุดิบรวมเป็น 100% เพื่อการคำนวณแบตช์ที่แม่นยำ</div>
""",
    },
    {
        "num": "6",
        "en_title": "Production Plan",
        "th_title": "แผนการผลิต",
        "img": "05-production-plan.png",
        "en_content": """
<p>The <strong>Production Plan</strong> page is used to schedule and organize production runs.</p>
<h4>Steps to Create a Plan:</h4>
<ol>
  <li>Select a <strong>SKU</strong> from the dropdown.</li>
  <li>Enter the <strong>Total Target Volume (kg)</strong>.</li>
  <li>Select the <strong>Plant/Production Line</strong>.</li>
  <li>Click <strong>"Create Plan"</strong> — The system automatically calculates the number of batches required based on the plant's batch capacity.</li>
</ol>
<h4>Plan List:</h4>
<p>The left panel shows all production plans. Click on a plan to see its batches and SKU details on the right panel.</p>
<div class="tip"><strong>💡 Tip:</strong> Plans can be printed for distribution to the production floor.</div>
""",
        "th_content": """
<p>หน้า <strong>แผนการผลิต</strong> ใช้สำหรับจัดตารางและจัดระเบียบรอบการผลิต</p>
<h4>ขั้นตอนการสร้างแผน:</h4>
<ol>
  <li>เลือก <strong>SKU</strong> จากเมนูดรอปดาวน์</li>
  <li>กรอก <strong>ปริมาณเป้าหมายรวม (กก.)</strong></li>
  <li>เลือก <strong>โรงงาน/สายการผลิต</strong></li>
  <li>คลิก <strong>"สร้างแผน"</strong> — ระบบจะคำนวณจำนวนแบตช์ที่ต้องการโดยอัตโนมัติตามความจุแบตช์ของโรงงาน</li>
</ol>
<h4>รายการแผน:</h4>
<p>แผงด้านซ้ายแสดงแผนการผลิตทั้งหมด คลิกที่แผนเพื่อดูแบตช์และรายละเอียด SKU ในแผงด้านขวา</p>
<div class="tip"><strong>💡 เคล็ดลับ:</strong> สามารถพิมพ์แผนเพื่อแจกจ่ายไปยังพื้นที่การผลิตได้</div>
""",
    },
    {
        "num": "7",
        "en_title": "Batch Prepare (Pre-Batch Weighing)",
        "th_title": "เตรียมแบตช์ (ชั่งน้ำหนัก Pre-Batch)",
        "img": "06-pre-batch.png",
        "en_content": """
<p>The <strong>Batch Prepare</strong> page is the core operational screen where operators weigh ingredients for each batch.</p>
<h4>Workflow:</h4>
<ol>
  <li>Select a <strong>Production Plan</strong> from the list.</li>
  <li>Select a specific <strong>Batch</strong> to work on.</li>
  <li>The system displays each ingredient required with its <strong>target volume</strong>.</li>
  <li><strong>Scan the ingredient barcode</strong> to identify the material.</li>
  <li><strong>Place the ingredient on the scale</strong> — The system reads the weight in real-time via MQTT integration with physical scales.</li>
  <li>Confirm the weight and move to the next ingredient.</li>
</ol>
<h4>Scale Integration:</h4>
<p>The system connects to industrial scales through an MQTT bridge. Weight readings are displayed in real-time with stability indicators.</p>
""",
        "th_content": """
<p>หน้า <strong>เตรียมแบตช์</strong> เป็นหน้าจอปฏิบัติการหลักที่พนักงานชั่งวัตถุดิบสำหรับแต่ละแบตช์</p>
<h4>ขั้นตอนการทำงาน:</h4>
<ol>
  <li>เลือก <strong>แผนการผลิต</strong> จากรายการ</li>
  <li>เลือก <strong>แบตช์</strong> เฉพาะที่จะทำงาน</li>
  <li>ระบบจะแสดงวัตถุดิบแต่ละรายการที่ต้องการพร้อม <strong>ปริมาณเป้าหมาย</strong></li>
  <li><strong>สแกนบาร์โค้ดวัตถุดิบ</strong> เพื่อระบุวัสดุ</li>
  <li><strong>วางวัตถุดิบบนเครื่องชั่ง</strong> — ระบบอ่านน้ำหนักแบบเรียลไทม์ผ่านการเชื่อมต่อ MQTT กับเครื่องชั่งจริง</li>
  <li>ยืนยันน้ำหนักและไปยังวัตถุดิบถัดไป</li>
</ol>
<h4>การเชื่อมต่อเครื่องชั่ง:</h4>
<p>ระบบเชื่อมต่อกับเครื่องชั่งอุตสาหกรรมผ่าน MQTT Bridge การอ่านน้ำหนักจะแสดงแบบเรียลไทม์พร้อมตัวบ่งชี้ความเสถียร</p>
""",
    },
    {
        "num": "8",
        "en_title": "Packing List",
        "th_title": "รายการบรรจุ",
        "img": "07-packing-list.png",
        "en_content": """
<p>The <strong>Packing List</strong> page manages the final boxing and verification process.</p>
<h4>Features:</h4>
<ul>
  <li><strong>Production Plan List</strong> — View plans with their batch IDs, SKUs, volumes, and pack counts.</li>
  <li><strong>2-Step Verification</strong> — Scan an ingredient bag barcode, then scan the Box ID to confirm it is inside the correct box.</li>
  <li><strong>Confirm Packing Table</strong> — Finalize and save the packing configuration.</li>
  <li><strong>Print List</strong> — Queue box labels for printing. Generate and print batch box labels with all ingredient details.</li>
  <li><strong>Pre-Batch Scans Detailed List</strong> — View all scans associated with a selected batch.</li>
</ul>
<div class="warning"><strong>⚠️ Important:</strong> Always verify scans before confirming the packing table.</div>
""",
        "th_content": """
<p>หน้า <strong>รายการบรรจุ</strong> จัดการกระบวนการบรรจุกล่องและตรวจสอบขั้นสุดท้าย</p>
<h4>คุณสมบัติ:</h4>
<ul>
  <li><strong>รายการแผนการผลิต</strong> — ดูแผนพร้อม Batch ID, SKU, ปริมาณ, และจำนวนแพ็ค</li>
  <li><strong>การตรวจสอบ 2 ขั้นตอน</strong> — สแกนบาร์โค้ดถุงวัตถุดิบ จากนั้นสแกน Box ID เพื่อยืนยันว่าอยู่ในกล่องที่ถูกต้อง</li>
  <li><strong>ยืนยันตาราง Packing</strong> — สรุปและบันทึกการตั้งค่าการบรรจุ</li>
  <li><strong>รายการพิมพ์</strong> — คิวฉลากกล่องสำหรับพิมพ์ สร้างและพิมพ์ฉลากกล่องแบตช์พร้อมรายละเอียดวัตถุดิบทั้งหมด</li>
  <li><strong>รายการสแกน Pre-Batch โดยละเอียด</strong> — ดูการสแกนทั้งหมดที่เกี่ยวข้องกับแบตช์ที่เลือก</li>
</ul>
<div class="warning"><strong>⚠️ สำคัญ:</strong> ตรวจสอบการสแกนก่อนยืนยันตาราง Packing เสมอ</div>
""",
    },
    {
        "num": "9",
        "en_title": "User Management (Admin)",
        "th_title": "จัดการผู้ใช้ (แอดมิน)",
        "img": "09-user-config.png",
        "en_content": """
<p>The <strong>User Management</strong> page is for administrators to manage user accounts and permissions.</p>
<h4>Features:</h4>
<ul>
  <li><strong>User List</strong> — Search and view all users with Name, Email, Role, Department, and Status.</li>
  <li><strong>Add User</strong> — Create new user accounts with username, email, password, role, and department.</li>
  <li><strong>Manage User</strong> — Click "Manage" to edit user information, change password, and configure permissions.</li>
  <li><strong>Permissions</strong> — Toggle individual page access for each user (Ingredient Intake, SKU, Production Plan, etc.).</li>
  <li><strong>Delete User</strong> — Remove user accounts (requires confirmation).</li>
</ul>
""",
        "th_content": """
<p>หน้า <strong>จัดการผู้ใช้</strong> สำหรับผู้ดูแลระบบเพื่อจัดการบัญชีผู้ใช้และสิทธิ์</p>
<h4>คุณสมบัติ:</h4>
<ul>
  <li><strong>รายการผู้ใช้</strong> — ค้นหาและดูผู้ใช้ทั้งหมดพร้อมชื่อ อีเมล บทบาท แผนก และสถานะ</li>
  <li><strong>เพิ่มผู้ใช้</strong> — สร้างบัญชีผู้ใช้ใหม่ด้วยชื่อผู้ใช้ อีเมล รหัสผ่าน บทบาท และแผนก</li>
  <li><strong>จัดการผู้ใช้</strong> — คลิก "จัดการ" เพื่อแก้ไขข้อมูลผู้ใช้ เปลี่ยนรหัสผ่าน และตั้งค่าสิทธิ์</li>
  <li><strong>สิทธิ์</strong> — สลับการเข้าถึงหน้าแต่ละหน้าสำหรับผู้ใช้แต่ละคน</li>
  <li><strong>ลบผู้ใช้</strong> — ลบบัญชีผู้ใช้ (ต้องยืนยัน)</li>
</ul>
""",
    },
    {
        "num": "10",
        "en_title": "System Dashboard (Admin)",
        "th_title": "แดชบอร์ดระบบ (แอดมิน)",
        "img": "10-system-dashboard.png",
        "en_content": """
<p>The <strong>System Dashboard</strong> provides real-time monitoring of the server infrastructure.</p>
<h4>Metrics Displayed:</h4>
<ul>
  <li><strong>PC Information</strong> — Hostname, IP Address, OS, Architecture, CPU Model.</li>
  <li><strong>System Uptime</strong> — Boot time and uptime duration.</li>
  <li><strong>CPU Usage</strong> — Real-time CPU utilization percentage with circular gauge.</li>
  <li><strong>Memory (RAM)</strong> — Memory usage with used/total display.</li>
  <li><strong>Storage (Disk)</strong> — Disk usage with used/total display.</li>
  <li><strong>Network Traffic</strong> — Bytes sent and received.</li>
  <li><strong>History Charts</strong> — CPU and Memory usage over the last 1 hour.</li>
</ul>
""",
        "th_content": """
<p><strong>แดชบอร์ดระบบ</strong> ให้การตรวจสอบโครงสร้างพื้นฐานของเซิร์ฟเวอร์แบบเรียลไทม์</p>
<h4>เมตริกที่แสดง:</h4>
<ul>
  <li><strong>ข้อมูล PC</strong> — ชื่อโฮสต์, ที่อยู่ IP, OS, สถาปัตยกรรม, รุ่น CPU</li>
  <li><strong>เวลาทำงานของระบบ</strong> — เวลาบูตและระยะเวลาทำงาน</li>
  <li><strong>การใช้ CPU</strong> — เปอร์เซ็นต์การใช้ CPU แบบเรียลไทม์พร้อมมาตรวัดวงกลม</li>
  <li><strong>หน่วยความจำ (RAM)</strong> — การใช้หน่วยความจำพร้อมแสดงใช้แล้ว/ทั้งหมด</li>
  <li><strong>พื้นที่จัดเก็บ (ดิสก์)</strong> — การใช้ดิสก์พร้อมแสดงใช้แล้ว/ทั้งหมด</li>
  <li><strong>ทราฟฟิกเครือข่าย</strong> — ไบต์ที่ส่งและรับ</li>
  <li><strong>กราฟประวัติ</strong> — การใช้ CPU และหน่วยความจำในช่วง 1 ชั่วโมงที่ผ่านมา</li>
</ul>
""",
    },
]

# ─── Build HTML ───
css = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Sarabun', 'Segoe UI', sans-serif; color: #333; line-height: 1.7; background: #fff; }
  .cover { page-break-after: always; display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 100vh; background: linear-gradient(135deg, #1565c0, #0d47a1); color: white; text-align: center; padding: 60px; }
  .cover h1 { font-size: 3.5em; font-weight: 700; margin-bottom: 10px; }
  .cover h2 { font-size: 1.8em; font-weight: 300; margin-bottom: 30px; opacity: 0.9; }
  .cover .meta { font-size: 1.1em; opacity: 0.7; margin-top: 40px; }
  .toc { page-break-after: always; padding: 60px 80px; }
  .toc h2 { font-size: 2em; color: #1565c0; border-bottom: 3px solid #1565c0; padding-bottom: 10px; margin-bottom: 30px; }
  .toc ul { list-style: none; }
  .toc li { padding: 8px 0; font-size: 1.15em; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; }
  .toc li .th-title { color: #666; font-size: 0.95em; }
  .chapter { page-break-before: always; padding: 40px 60px; }
  .chapter-header { background: linear-gradient(135deg, #1565c0, #42a5f5); color: white; padding: 25px 35px; border-radius: 8px; margin-bottom: 30px; }
  .chapter-header h2 { font-size: 1.8em; margin-bottom: 5px; }
  .chapter-header .th { font-size: 1.3em; opacity: 0.85; font-weight: 300; }
  .bilingual { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-top: 20px; }
  .lang-block { padding: 20px; border-radius: 8px; }
  .lang-block.en { background: #f5f9ff; border-left: 4px solid #1565c0; }
  .lang-block.th { background: #fff8f0; border-left: 4px solid #ff9800; }
  .lang-label { font-size: 0.8em; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; color: #999; margin-bottom: 12px; }
  .lang-block h4 { color: #1565c0; margin: 15px 0 8px; }
  .lang-block.th h4 { color: #e65100; }
  .lang-block p { margin-bottom: 10px; }
  .lang-block ol, .lang-block ul { margin: 8px 0 12px 20px; }
  .lang-block li { margin-bottom: 4px; }
  .screenshot { width: 100%; max-width: 100%; border: 2px solid #ddd; border-radius: 8px; margin: 15px 0; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
  .tip { background: #e8f5e9; border-left: 4px solid #4caf50; padding: 12px 16px; border-radius: 4px; margin: 12px 0; font-size: 0.95em; }
  .warning { background: #fff3e0; border-left: 4px solid #ff9800; padding: 12px 16px; border-radius: 4px; margin: 12px 0; font-size: 0.95em; }
  .no-img { background: #f5f5f5; padding: 40px; text-align: center; color: #999; border-radius: 8px; margin: 15px 0; }
  .footer { text-align: center; color: #999; font-size: 0.85em; padding: 20px; border-top: 1px solid #eee; margin-top: 40px; }
  @media print {
    body { font-size: 11pt; }
    .chapter { page-break-before: always; padding: 20px 40px; }
    .bilingual { gap: 15px; }
    .screenshot { max-width: 90%; page-break-inside: avoid; }
  }
</style>
"""

html_parts = [f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>xMixing User Manual / คู่มือผู้ใช้ xMixing</title>
{css}
</head>
<body>

<!-- COVER PAGE -->
<div class="cover">
  <h1>🏭 xMixing</h1>
  <h2>User Manual / คู่มือผู้ใช้</h2>
  <p style="font-size:1.3em;">Batch Management &amp; Mixing Control System</p>
  <p style="font-size:1.1em; opacity:0.8;">ระบบจัดการแบตช์และควบคุมการผสม</p>
  <div class="meta">
    <p>Version 1.0.0 | February 2026</p>
    <p>devTeam@xDev.co.th</p>
  </div>
</div>

<!-- TABLE OF CONTENTS -->
<div class="toc">
  <h2>📋 Table of Contents / สารบัญ</h2>
  <ul>
"""]

for ch in chapters:
    html_parts.append(f'    <li><span>Chapter {ch["num"]}: {ch["en_title"]}</span> <span class="th-title">{ch["th_title"]}</span></li>\n')

html_parts.append("  </ul>\n</div>\n\n")

# Chapters
for ch in chapters:
    img = img_tag(ch["img"], ch["en_title"])
    html_parts.append(f"""
<!-- CHAPTER {ch["num"]} -->
<div class="chapter">
  <div class="chapter-header">
    <h2>Chapter {ch["num"]}: {ch["en_title"]}</h2>
    <div class="th">บทที่ {ch["num"]}: {ch["th_title"]}</div>
  </div>

  {img}

  <div class="bilingual">
    <div class="lang-block en">
      <div class="lang-label">🇬🇧 English</div>
      {ch["en_content"]}
    </div>
    <div class="lang-block th">
      <div class="lang-label">🇹🇭 ภาษาไทย</div>
      {ch["th_content"]}
    </div>
  </div>
</div>
""")

# Footer
html_parts.append("""
<div class="footer">
  <p>© 2026 xMixing by xDev.co.th — All rights reserved.</p>
  <p>To save as PDF: Open this file in a browser → File → Print → Save as PDF</p>
</div>

</body>
</html>
""")

# ─── Write Output ───
output_path = os.path.join(SCRIPT_DIR, "xMixing-UserManual.html")
with open(output_path, "w", encoding="utf-8") as f:
    f.write("".join(html_parts))

print(f"✅ Manual generated: {output_path}")
print(f"   Screenshots embedded: {sum(1 for c in chapters if img_to_base64(c['img']))}/{len(chapters)}")
print(f"   Chapters: {len(chapters)}")
print(f"\n📄 To create PDF:")
print(f"   1. Open the HTML file in Chrome/Safari")
print(f"   2. Press Cmd+P (Print)")
print(f"   3. Select 'Save as PDF'")
print(f"   4. Set margins to 'None' or 'Minimum'")

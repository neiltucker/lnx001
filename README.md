# LNX001  
## Linux Administration Essentials

[![Software Tutorial Services](https://img.shields.io/badge/Instructor--Led%20Training-SoftwareTutorialServices.com-0078D4?style=flat-square)](https://www.softwaretutorialservices.com/course/lnx001)
[![Courseware Studio](https://img.shields.io/badge/AI%20Curriculum%20Authoring-CoursewareStudio.ai-6366F1?style=flat-square)](https://coursewarestudio.ai)
[![Ubuntu 24.04 LTS](https://img.shields.io/badge/Platform-Ubuntu%2024.04%20LTS-E95420?style=flat-square&logo=ubuntu)](https://ubuntu.com)
[![SCORM 2004 Ready](https://img.shields.io/badge/LMS-SCORM%202004%20Certified-10B981?style=flat-square)](https://coursewarestudio.ai)

**Course Delivery & Live Instruction:** [Software Tutorial Services — LNX001](https://www.softwaretutorialservices.com/course/lnx001)  
**Curriculum Authoring & LMS Packaging:** [Courseware Studio](https://coursewarestudio.ai)

**Duration:** 1 Day (6 Hours)  
**Modules:** 4 Modules + 1 Integrated Capstone Lab  
**Audience Level:** Beginner / Foundational  
**Delivery Formats:** Instructor-Led Training (ILT) · Intensive Bootcamp · Self-Paced eLearning  
**Target Platform:** Ubuntu 24.04 LTS (Windows WSL2, Hyper-V, VMware, or Cloud VM)

---

## Course Overview

**Linux Administration Essentials (LNX001)** is an intensive, one-day foundational course designed for IT professionals, system administrators, DevOps engineers, and technical support specialists who need practical, production-ready skills on modern Linux systems.

Centered on Ubuntu 24.04 LTS, students learn core terminal navigation, administrative user and group provisioning, POSIX file permissions, hardware discovery, block storage partitioning, filesystem formatting, persistent `/etc/fstab` mounting, modern network configuration, OpenSSH daemon hardening, process monitoring, central log inspection with `journald`, and host defense using the Uncomplicated Firewall (UFW).

Every lesson includes hands-on terminal exercises that can be completed locally on your own computer (via WSL2 or virtual machine) or through free cloud resources.

---

## At Course Completion

After completing this course, students will be able to:

- **Navigate the Linux Filesystem:** Understand the Filesystem Hierarchy Standard (FHS), execute core terminal utilities, and build stream redirection and pipeline workflows.
- **Administer Users & Security Boundaries:** Provision user accounts, manage supplementary groups, apply standard and special POSIX permissions (`chmod`, `chown`, `umask`), and configure granular administrative delegation using `/etc/sudoers.d/`.
- **Manage Storage & Volumes:** Inspect hardware devices, partition block storage using `fdisk`, format ext4 filesystems, and establish reliable persistent mount points via `/etc/fstab` using UUIDs.
- **Configure & Troubleshoot Networking:** Query IP interfaces and default gateway routing, test DNS resolution, deploy OpenSSH Server, and harden SSH access against unauthorized intrusion.
- **Control Processes & Secure the Host:** Monitor system resources with `top` and `ps`, control execution with process signals, query centralized systemd logs with `journalctl`, and enforce perimeter defense policies with UFW.
- **Execute Capstone Provisioning:** Synthesize all four modules into an end-to-end edge server provisioning and security lockdown scenario.

---

## Prerequisites

Students attending this course should have:

- Basic understanding of computer operating systems and hardware architecture
- Familiarity with foundational computing concepts and general command-line interfaces
- No prior Linux or bash shell scripting experience is required

---

## Lab Environment & Automated Setup

Students require an Ubuntu 24.04 LTS environment (running locally under Windows WSL2, Hyper-V, VirtualBox, or as a cloud instance) with sudo/root privileges.

### Automated Setup Script (`LNX-001-Setup.ps1`)
For Windows host environments (WSL2 / Hyper-V), run the included automated setup script in PowerShell as Administrator:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
.\LNX-001-Setup.ps1
```

The script automatically validates media prerequisites, creates deployment folder hierarchies, configures validation logging, and pre-stages standard lab user credentials.

### Standard Classroom Lab Credentials
* **Linux Administrative User:** `adminz` (Password: `Pa$$w0rdPa$$w0rd`, sudo privilege)
* **Linux Student User:** `student` (Password: `Pa$$w0rd`, sudo privilege)
* **Linux Superuser:** `root` (Password: `Pa$$w0rdPa$$w0rd`)

*(Note: These are classroom sandbox credentials. Never use default lab passwords in production environments.)*

---

# Course Outline

## Module 1: Linux User and Group Administration

**Scheduled Duration:** 90 min (45 min Lecture/Demo · 30 min Lab · 15 min Review)

### Lessons
- **Lesson 1:** Managing User Accounts and Group Memberships
- **Lesson 2:** Understanding Linux File Ownership and POSIX Permissions
- **Lesson 3:** Sudo Architecture and Administrative Access Control

### Hands-On Lab Exercise
- **Lab 1:** Configuring Users, Groups, and Permissions on Ubuntu
  - Create secure administrative collaboration groups (`groupadd`)
  - Provision unique local auditor user accounts with bash shells (`useradd`, `passwd`)
  - Assign secondary group memberships safely (`usermod -aG`)
  - Delegate restricted privilege boundaries via drop-in files in `/etc/sudoers.d/` (`visudo`)
  - Secure shared compliance directories with mode `770` and setgid group inheritance

### Learning Objectives
- Create and manage local user accounts and groups using terminal commands
- Configure standard Linux file permissions and ownership configurations
- Utilize administrative privileges securely with the sudo configuration framework
- Apply least-privilege principles to shared folder collaborative environments

---

## Module 2: Hardware and File System Management

**Scheduled Duration:** 90 min (45 min Lecture/Demo · 30 min Lab · 15 min Review)

### Lessons
- **Lesson 1:** Hardware Discovery and Querying Tools (`lshw`, `lsblk`, `lspci`, `lscpu`)
- **Lesson 2:** Disk Partitioning and Filesystem Creation (`fdisk`, `mkfs.ext4`)
- **Lesson 3:** The Mounting Mechanism and Persistent `/etc/fstab` Configuration

### Hands-On Lab Exercise
- **Lab 2:** Adding and Mounting a New Virtual Storage Volume
  - Query and inventory existing block devices and system storage topology
  - Provision and attach virtual storage volumes using loopback devices (`losetup`)
  - Partition block devices with standard MBR/GPT partition tables (`fdisk`)
  - Format partitions with the standard `ext4` filesystem (`mkfs.ext4`)
  - Mount filesystems manually and verify mount status (`mount`, `findmnt`)
  - Configure persistent boot mounting in `/etc/fstab` using device UUIDs (`blkid`)

### Learning Objectives
- Identify and query system hardware information using built-in system tools
- Perform basic partition operations on available system storage devices
- Format and mount custom file systems reliably across system reboots
- Verify storage quotas, disk usage, and inode allocations with `df` and `du`

---

## Module 3: Linux Network Configuration and Services

**Scheduled Duration:** 90 min (45 min Lecture/Demo · 30 min Lab · 15 min Review)

### Lessons
- **Lesson 1:** Network Interface Configuration and Modern Tooling (`ip`, `netplan`)
- **Lesson 2:** Diagnostic Utilities for Network Troubleshooting (`ping`, `traceroute`, `ss`, `resolvectl`)
- **Lesson 3:** Configuring and Hardening Secure Shell (SSH) Remote Access

### Hands-On Lab Exercise
- **Lab 3:** Configuring Interfaces and Securing SSH
  - Inspect active network interfaces, IP addresses, and CIDR masks (`ip addr show`)
  - Query kernel routing tables and default internet gateways (`ip route`)
  - Test end-to-end packet delivery and DNS resolution (`ping`, `resolvectl`)
  - Deploy and enable the OpenSSH Server daemon (`openssh-server`, `systemctl`)
  - Harden SSH configurations: disable root login, enforce key-based access, and restrict allowed users
  - Validate sshd configuration syntax (`sshd -t`) and verify listening sockets (`ss -tulpn`)

### Learning Objectives
- Inspect and configure active network interface properties and routing tables
- Verify remote network connectivity using standard diagnostic utilities
- Deploy, maintain, and secure the OpenSSH server daemon for remote management
- Audit active sockets and service listeners on local network ports

---

## Module 4: Linux Security, Logging, and Process Management

**Scheduled Duration:** 90 min (45 min Lecture/Demo · 30 min Lab · 15 min Review)

### Lessons
- **Lesson 1:** Host Protection with the Uncomplicated Firewall (UFW)
- **Lesson 2:** Process Administration and System Monitoring (`top`, `ps`, `kill`, `pkill`)
- **Lesson 3:** Log Analysis and System Troubleshooting via Systemd Journal (`journalctl`)

### Hands-On Lab Exercise
- **Lab 4:** Securing Services and Analyzing Log Events on Ubuntu
  - Launch, monitor, and background simulation workloads (`ps aux`, `top`)
  - Manage running services and terminate rogue processes using signals (`kill -15`, `kill -9`)
  - Establish default ingress/egress firewall policies (`ufw default deny incoming`)
  - Add granular firewall rules for SSH and web traffic (`ufw allow 22/tcp`)
  - Enable and audit UFW operational state (`ufw status verbose`)
  - Inspect central system logs and audit security events using `journalctl`

### Learning Objectives
- Configure host-level firewall protections with the Uncomplicated Firewall (UFW)
- Monitor, manage, and scale system execution processes via terminal tools
- Analyze central administrative system logs to debug platform failures
- Formulate an end-to-end operational checklist for production Linux servers

---

## Day 1 Capstone Lab: Edge Sensor Station Provisioning and Security Hardening

**Estimated Duration:** 90–120 minutes (Bootcamp delivery: up to 240 minutes)  
**Integrated Skills:** Modules 1, 2, 3, and 4  

In this comprehensive scenario, learners are assigned the role of an Infrastructure Engineer tasked with taking a fresh Ubuntu 24.04 LTS host and preparing it as a secure, production-grade edge telemetry sensor station:

1. **System Provisioning:** Create isolated service accounts (`sensor_svc`) and operational groups (`sensor_ops`) with dedicated home directories and shell access.
2. **Delegation Controls:** Implement passwordless `sudo` execution limited strictly to service management binaries via `/etc/sudoers.d/90-sensor-ops`.
3. **Storage Pipeline:** Attach virtual storage media, partition, format with `ext4`, mount persistently at `/mnt/sensor_data` via UUID in `/etc/fstab`, and set group collaboration permissions.
4. **Network & SSH Hardening:** Verify routing and DNS, configure the OpenSSH daemon to forbid root logins, restrict allowed users, and eliminate insecure ciphers.
5. **Firewall & Logging:** Establish a default-deny incoming UFW perimeter, allow necessary telemetry and management ports, start telemetry collection background daemons, and audit event logs using `journalctl`.

---

## 📦 Repository Deliverables & Course Resources

This repository contains the full suite of instructional, student, and deployment materials for LNX001:

| Resource | File Name | Description |
|---|---|---|
| 📖 **Course Syllabus** | [`LNX-001_EN_Syllabus.pdf`](./LNX-001_EN_Syllabus.pdf) | Official course syllabus, timing breakdown, and learning objectives |
| 🧑‍🏫 **Trainer Prep Guide** | [`LNX-001_EN_TrainerPreparationGuide.pdf`](./LNX-001_EN_TrainerPreparationGuide.pdf) | Complete 41-page instructor delivery guide, pacing, Q&A keys, and assessments |
| 🛠️ **Hands-On Lab Guide** | [`LNX-001-EN_LabGuide.md`](./LNX-001-EN_LabGuide.md) | Step-by-step student exercise walkthrough for all 4 labs and the Capstone Lab |
| ⚡ **Quick Reference Guide** | [`Day-01-QuickReference.html`](./Day-01-QuickReference.html) · [`.pdf`](./Day-01-QuickReference.pdf) | Standalone quick-reference desk guide with essential Ubuntu administrative commands |
| 🎓 **Interactive SCORM LMS** | [Courseware Studio](https://coursewarestudio.ai) | SCORM 2004 4th Edition certified interactive package with built-in AI Tutor available via authoring platform |
| ⚙️ **Automated Lab Setup** | [`LNX-001-Setup.ps1`](./LNX-001-Setup.ps1) | PowerShell setup script to configure local Windows/WSL2/Hyper-V lab environments |
| 📄 **Course Setup Notes** | [`LNX-001-Readme.txt`](./LNX-001-Readme.txt) | Delivery guidance, classroom links, and environment licensing notes |

---

## 🎓 Instructor Delivery & Custom Courseware

* **Live Corporate Training Delivery:** To schedule this 1-day course delivered by experienced enterprise Linux instructors for your team, visit **[Software Tutorial Services — LNX001](https://www.softwaretutorialservices.com/course/lnx001)**.
* **AI Course Authoring & LMS Packaging:** Need to adapt this syllabus, generate tailored student manuals, create PowerPoint slide decks, or export interactive LMS packages? Use **[Courseware Studio](https://coursewarestudio.ai)**.
* **Instructor Classroom Tools:** Pacing lab sessions? Use our free **[Timer3](https://github.com/neiltucker/timer3)** presentation timer.

---

## 📝 License & Trademarks

Course materials created in partnership with [Software Tutorial Services](https://www.softwaretutorialservices.com) and [Courseware Studio](https://coursewarestudio.ai).  
Ubuntu is a registered trademark of Canonical Ltd. All other trademarks belong to their respective owners.

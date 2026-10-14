# LNX-001: Linux Administration Essentials
## Hands-On Lab Guide & Exercise Manual

[![Software Tutorial Services](https://img.shields.io/badge/Instructor--Led%20Training-SoftwareTutorialServices.com-0078D4?style=flat-square)](https://www.softwaretutorialservices.com/course/lnx001)
[![Courseware Studio](https://img.shields.io/badge/AI%20Curriculum%20Authoring-CoursewareStudio.ai-6366F1?style=flat-square)](https://coursewarestudio.ai)

**Course Delivery & Instructor Access:** [Software Tutorial Services](https://www.softwaretutorialservices.com/course/lnx001)  
**Course Authoring & LMS Packaging:** [Courseware Studio](https://coursewarestudio.ai)  
**Target Platform:** Ubuntu 24.04 LTS (Local VM, WSL2, or Cloud Instance)  
**Prerequisite:** Local account with standard `sudo` administrative rights

---

# Lab: Configuring Users, Groups, and Permissions on Ubuntu

**Objective:** Log into the Ubuntu virtual environment, create administrative user accounts, define secure collaborative groups, and apply file access control restrictions.

**Estimated Time:** 30 minutes

**Platform:** Ubuntu 24.04 LTS (Running on Windows WSL2 or Hyper-V)

**Prerequisites:**
* A running Ubuntu 24.04 LTS local virtual machine or WSL2 instance
* An active user account with sudo privileges to perform initial administrative tasks

## Procedures

### Step 1: Create a new secure collaboration group in Ubuntu

In this step, you will create a local group named `audit_group`. This group will be used later to manage administrative and file access control permissions.

Open your Ubuntu terminal and run the following command to create the group:

```bash
sudo groupadd audit_group
```

**Expected Output:**
The terminal returns to the command prompt without error.

*✔ Verification:* Confirm the group was successfully created by searching for it in `/etc/group`:

```bash
grep "audit_group" /etc/group
```
Expected output should display: `audit_group:x:[GID]:`

### Step 2: Create a unique local auditor user account

Now, create a new local user account utilizing your unique initials. Replace `learnerInitials` with your value (e.g., `auditor_nt`).

Run the following command to create the user account with a home directory and default bash shell:

```bash
sudo useradd -m -s /bin/bash auditor_learnerInitials
```

Next, set a password for the newly created user (e.g., `SecurePass123!`):

```bash
sudo passwd auditor_learnerInitials
```

Enter and confirm the password when prompted.

**Expected Output:**
passwd: password updated successfully

*✔ Verification:* Check that the user was created with the correct shell and home directory settings:

```bash
grep "auditor_learnerInitials" /etc/passwd
```

### Step 3: Assign the new user to the secure collaboration group

Associate the newly created auditor account with the `audit_group` group to manage administrative scope. Use the `usermod` command to append the user to the group without removing existing memberships.

Run the following command:

```bash
sudo usermod -aG audit_group auditor_learnerInitials
```

**Expected Output:**
The terminal returns to the command prompt without error.

*✔ Verification:* Verify that the user is successfully assigned to the group:

```bash
groups auditor_learnerInitials
```
Expected output must contain `audit_group`.

### Step 4: Configure restrictive sudo access for the audit group

To implement administrative access control securely, you will configure sudo privileges for members of `audit_group` using a drop-in configuration file within `/etc/sudoers.d/` rather than modifying the main configuration file directly.

Create and open a custom file inside `/etc/sudoers.d/` using `visudo` to prevent syntax issues:

```bash
sudo visudo -f /etc/sudoers.d/audit_group
```

Add the following single rule to the file. This allows all users in the `audit_group` to run `apt update` and check log tails without requiring complete root permissions:

```bash
%audit_group ALL=(ALL:ALL) /usr/bin/apt update, /usr/bin/tail
```

Save and exit the editor (in nano, press `Ctrl+O`, `Enter`, then `Ctrl+X`).

**Expected Output:**
The rule is saved successfully, and the command exits without syntax error messages.

*✔ Verification:* Confirm that the syntax of the new sudoers configuration is correct:

```bash
sudo visudo -c
```

### Step 5: Create and secure a shared compliance directory

To enforce standard Linux file permissions and ownership, create a shared directory that only members of the `audit_group` can read, write, and access.

Create the target directory:

```bash
sudo mkdir -p /srv/compliance
```

Change the ownership of the directory to user `root` and group `audit_group`:

```bash
sudo chown root:audit_group /srv/compliance
```

Configure permissions so that the owner (root) and group members (audit_group) have read, write, and execute permissions (7), while all other users have no access (0):

```bash
sudo chmod 770 /srv/compliance
```

**Expected Output:**
The terminal returns to the command prompt without error.

*✔ Verification:* Verify the ownership and permissions on the newly created directory:

```bash
ls -ld /srv/compliance
```
Expected output must match: `drwxrwx--- 2 root audit_group`

### Step 6: Switch user context and verify permissions and administrative capabilities

Verify that your configurations work under the context of the newly created auditor account.

Switch to the new user session:

```bash
su - auditor_learnerInitials
```

Attempt to navigate to and write a file in the secured `/srv/compliance` directory:

```bash
cd /srv/compliance
touch test_file.txt
```

Test the configured sudo administrative permissions by running the allowed `apt update` command:

```bash
sudo apt update
```

Verify that unauthorized administrative commands (like running an interactive bash shell as root) are blocked for this user:

```bash
sudo -i
```

**Expected Output:**
The file `test_file.txt` is successfully created inside `/srv/compliance`. The `sudo apt update` completes. The `sudo -i` command fails with a message indicating the user is not allowed to execute this command as root.

*✔ Verification:* Verify that the test file exists and contains the correct group ownership:

```bash
ls -l /srv/compliance/test_file.txt
```
Expected output should list `auditor_learnerInitials` as the owner and `audit_group` or `auditor_learnerInitials` as the group.

## Troubleshooting
**Problem:** The command 'sudo' prompt asks for a password, but typing displays nothing.**Solution:** This is normal behavior on Linux systems for security reasons. Type your password blindly and press Enter.**Problem:** When configuring sudoers, visudo reports 'visudo: >>> /etc/sudoers.d/audit_group: syntax error <<<'**Solution:** Select 'e' to edit the file again and review the syntax. Ensure the group is prefixed with % (e.g. `%audit_group`) and the command paths match the absolute path on your filesystem (such as `/usr/bin/apt`). Do not save a broken file, as it may lock you out of admin privileges.**Problem:** The newly created auditor user gets 'Permission denied' when trying to access `/srv/compliance`.**Solution:** Verify the user was successfully added to the group by running `groups`. If you added the user to the group while already switched to that user's session, you must log out (`exit`) and run `su - auditor_learnerInitials` again to load the updated group environment variable.
## Challenge Exercise

### Enforce Shared Folder Collaboration (Optional)

Extend your knowledge of standard permissions by modifying the directory permissions on `/srv/compliance` so that any new files created inside it automatically inherit the `audit_group` group ownership, regardless of which user creates the file. Hint: Explore the setgid directory permission bit (`chmod g+s`). Verify your solution by creating a file with a different user who belongs to the `audit_group` and confirming its default group ownership matches `audit_group` automatically.

---

# Lab: Adding and Mounting a New Virtual Storage Volume

**Objective:** Simulate attaching a physical storage volume, configure partitions, format an ext4 filesystem, and map persistent mount configurations in fstab.

**Estimated Time:** 30 minutes

**Platform:** Ubuntu 24.04 LTS (Local VM or Cloud Instance)

**Prerequisites:**
* Access to an Ubuntu 24.04 LTS terminal with sudo privileges.

## Procedures

### Step 1: Query and identify existing storage devices on the system.

Before modifying storage, discover the current disk configuration to ensure you do not overwrite existing system data.

Run the following commands to display block devices and hardware details:

```bash
lsblk
sudo lshw -class disk
```

**Expected Output:**
An output showing the primary disk (usually `sda` or `vda`) along with its respective partitions, and hardware specs displaying the disk bus info.

*✔ Verification:* Confirm that your system's main disk partition layout (e.g., `/`, `/boot`) is visible and that no unpartitioned raw loop devices are currently mapped to `/var/tmp`.

### Step 2: Simulate adding a physical storage volume using a loop device.

To safely model adding a new virtual hard drive without disrupting your host hypervisor or cloud settings, you will create a 1 GB raw file and bind it as a loop block device.

Create a 1 GB raw image file in `/var/tmp`:

```bash
sudo dd if=/dev/zero of=/var/tmp/virtual_disk.img bs=1M count=1024
```

Bind the image file to the first available loop device:

```bash
sudo losetup -fP /var/tmp/virtual_disk.img
```

Identify which loop device was assigned:

```bash
losetup -a
```

*Note: Note down the loop device name (e.g., `/dev/loop8` or `/dev/loop20`). The rest of this lab assumes `/dev/loop8` is used. Adjust accordingly if your system assigns a different number.*

**Expected Output:**
`1024+0 records in` / `1024+0 records out` from `dd`, and `losetup -a` showing `/dev/loop8: [/var/tmp/virtual_disk.img]`.

*✔ Verification:* Run `lsblk` and check if your assigned loop device (e.g., `loop8`) is listed with a size of `1G`.

### Step 3: Partition the newly attached virtual block device.

Partition the new block device to host your filesystem. You will create a single primary partition using `fdisk`.

Open `fdisk` on your loop device:

```bash
sudo fdisk /dev/loop8
```

Inside the interactive `fdisk` prompt, enter the following commands in sequence:

* Type `n` and press **Enter** (to create a new partition).

* Type `p` and press **Enter** (to choose primary).

* Press **Enter** to accept the default partition number (`1`).

* Press **Enter** to accept the default first sector.

* Press **Enter** to accept the default last sector (allocates the entire 1 GB).

* Type `w` and press **Enter** to write the partition table to disk and exit.

Inform the kernel of the partition table changes:

```bash
sudo partx -a /dev/loop8
```

**Expected Output:**
fdisk outputs: `Created a new partition 1 of type &#39;Linux&#39; and of size 1023 MiB.` followed by `The partition table has been altered.`

*✔ Verification:* Run `lsblk` to verify that a child partition (e.g., `loop8p1`) now exists under your loop device parent.

### Step 4: Format the newly created partition with an ext4 filesystem.

Format the partition with the standard Linux robust filesystem, `ext4`.

Run the formatting utility:

```bash
sudo mkfs.ext4 /dev/loop8p1
```

**Expected Output:**
Output showing block allocation, superblocks, journal creation, and finally: `Writing superblocks and filesystem accounting information: done`.

*✔ Verification:* Run `sudo blkid /dev/loop8p1` and confirm that the output displays `TYPE="ext4"` and a unique `UUID` attribute.

### Step 5: Create a custom mount point and manually mount the filesystem.

Mount the newly formatted partition onto a localized mounting directory.

Create a new target mount directory utilizing your initials (replace `learnerInitials` with your actual initials, e.g., `nt`):

```bash
sudo mkdir -p /mnt/secure_storage_learnerInitials
```

Mount the partition manually:

```bash
sudo mount /dev/loop8p1 /mnt/secure_storage_learnerInitials
```

Verify that the storage has been attached and verify the available space:

```bash
df -h | grep secure_storage_learnerInitials
```

**Expected Output:**
The `df` output displays the partition `/dev/loop8p1` mounted on `/mnt/secure_storage_learnerInitials` with approximately 972M of available space.

*✔ Verification:* Run `mount | grep secure_storage_learnerInitials` to confirm the filesystem is mounted as `ext4` with standard read/write (`rw`) privileges.

### Step 6: Configure persistent mounting for the storage volume in fstab.

Ensure the filesystem mounts automatically upon reboot by mapping its UUID in `/etc/fstab`.

Retrieve the unique UUID for the partition:

```bash
sudo blkid -o value -s UUID /dev/loop8p1
```

Copy this exact UUID.

Open `/etc/fstab` in the nano text editor:

```bash
sudo nano /etc/fstab
```

Scroll to the bottom of the file and append a new line (replace `your_uuid_here` with the copied UUID, and `learnerInitials` with your initials):

```bash
UUID=your_uuid_here /mnt/secure_storage_learnerInitials ext4 defaults,nofail 0 2
```

*Note: The `nofail` option prevents system boot failures if this virtual loop file is ever unmapped.* 
Save and exit nano (**Ctrl+O**, **Enter**, **Ctrl+X**).

To test your configuration without rebooting, unmount the volume first:

```bash
sudo umount /mnt/secure_storage_learnerInitials
```

Now, mount all filesystems defined in `/etc/fstab`:

```bash
sudo mount -a
```

Check if the volume re-mounted successfully:

```bash
df -h | grep secure_storage_learnerInitials
```

**Expected Output:**
The `/etc/fstab` contains the new UUID mount definition. The final `df` command displays the filesystem successfully re-mounted automatically.

*✔ Verification:* Verify that no errors were thrown when running `sudo mount -a`, which confirms correct syntax in `/etc/fstab`.

## Troubleshooting
**Problem:** Command 'losetup -fP' returns 'No such file or directory' or similar error.**Solution:** Ensure you created the raw disk image file in the correct path first using the 'dd' command, and verify that '/var/tmp' exists on your terminal filesystem.**Problem:** The device partitions are not updating or '/dev/loop8p1' is missing.**Solution:** On some older kernels, loop device partition mapping is not automatic. Force partition table detection by executing 'sudo partx -a /dev/loop8' or running 'sudo kpartx -a /dev/loop8'.**Problem:** The system throws syntax errors or hangs when checking 'sudo mount -a'.**Solution:** Immediately open '/etc/fstab' with nano again and review your appended line. Ensure there are no spaces within 'defaults,nofail' (it must be a comma-separated list without spaces) and verify that the UUID exactly matches your block device UUID.
## Challenge Exercise

### Mount Verification and Report Script (Optional)

Write a bash shell script that checks whether the storage volume `/mnt/secure_storage_learnerInitials` is successfully mounted on the system.

Your script should:

* Query the active mount points.

* Output an alert message "[SUCCESS] Volume is active and secure" to the console if it is successfully mounted.

* Log the status, date, and storage utilization details of the partition to a file named `$HOME/mount_audit.log` only if the mount is detected.

---

# Lab: Configuring Interfaces and Securing SSH

**Objective:** Identify current interface details, test routing infrastructure, verify host availability, install OpenSSH, and implement default configuration hardening.

**Estimated Time:** 30 minutes

**Platform:** Windows with Ubuntu 24 VM

**Prerequisites:**
* Local computer running Windows with an active virtualization environment (e.g., Hyper-V, VirtualBox, or WSL2) hosting an Ubuntu 24.04 LTS instance.
* Administrative or sudo privileges on the Ubuntu 24.04 instance.
* An active, functioning internet connection on the Ubuntu instance.

## Procedures

### Step 1: Inspect active network interface configuration details

Open your terminal in the Ubuntu 24 instance. Use the modern `ip` toolset to inspect active network interfaces, their operational states, and assigned IP addresses.

Execute the following command to display active network link layer configurations:

```bash
ip link show
```

Next, view the assigned IP addresses on all network interfaces:

```bash
ip addr show
```

Identify and note down the name of your primary network interface (commonly starts with `eth` or `en`, such as `eth0` or `ens33`). You will need this interface name to reference in future network assessment operations.

**Expected Output:**
An output listing interfaces like `lo` (loopback) and a primary interface (e.g., `eth0` or `enp0s3`), showing state `UP` and containing assigned IPv4 and IPv6 details (e.g., `inet 10.0.2.15/24`).

*✔ Verification:* Confirm that your primary network interface lists a status of `<UP,BROADCAST,RUNNING,MULTICAST>` and displays a valid, non-loopback IP address under the `inet` line.

### Step 2: Inspect the default routing table and system gateways

To determine how the local Linux system directs traffic to external networks, inspect the active routing table.

Run the following command to view the IP routing entries:

```bash
ip route show
```

Identify the line starting with `default`. This line indicates the local gateway IP address to which all non-local packets are dispatched.

Example routing entry analysis:

* `default via 10.0.2.2 dev eth0 proto dhcp src 10.0.2.15 metric 100`

* In this example, `10.0.2.2` represents the default gateway.

**Expected Output:**
default via 10.0.2.2 dev eth0 proto dhcp src 10.0.2.15 metric 100
10.0.2.0/24 dev eth0 proto kernel scope link src 10.0.2.15 metric 100

*✔ Verification:* Verify that a routing rule exists beginning with the keyword `default`. Note the gateway IP address specified immediately after the `via` keyword.

### Step 3: Verify network connectivity and DNS name resolution

Use standard diagnostic tools to confirm low-level network reachability and domain resolution services. You will send exactly 3 ICMP echo request packets to verify network transmission stability.

First, test raw IP-based outbound reachability by pinging a public DNS server:

```bash
ping -c 3 8.8.8.8
```

Next, test DNS configuration and host domain resolution capability:

```bash
ping -c 3 google.com
```

**Expected Output:**
PING google.com (142.250.190.46) 56(84) bytes of data.
64 bytes from ...: icmp_seq=1 ttl=115 time=12.1 ms
64 bytes from ...: icmp_seq=2 ttl=115 time=11.8 ms
64 bytes from ...: icmp_seq=3 ttl=115 time=11.9 ms

--- google.com ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2003ms

*✔ Verification:* Ensure that the statistics output at the end of both commands indicates `0% packet loss` and a successful resolve of the domain name to an IP address.

### Step 4: Deploy the OpenSSH Server daemon

Install the server components necessary to configure secure remote administrative terminal sessions.

Begin by synchronizing the local package repository index to guarantee deployment of the latest updates:

```bash
sudo apt update
```

Once the update completes, install the OpenSSH server package using the package manager:

```bash
sudo apt install -y openssh-server
```

**Expected Output:**
Reading package lists... Done
Building dependency tree... Done
...
Setting up openssh-server ...
Created symlink /etc/systemd/system/sshd.service → /usr/lib/systemd/system/ssh.service.

*✔ Verification:* Confirm the service has installed and initialized properly by querying the system manager service status:
```bash
sudo systemctl status ssh
```
Ensure the status is listed as `active (running)`.

### Step 5: Harden the SSH daemon configuration

Modify administrative access capabilities and move the listening service to a custom port to reduce vulnerability to automated network probes.

Rather than modifying the default global configuration file directly, write a dedicated custom drop-in configuration file in the dynamic SSH daemon folder.

Create a new file called `99-hardened.conf` inside the directory `/etc/ssh/sshd_config.d/` using your custom SSH port (from the `customSshPort` variable, e.g., `2222`):

```bash
sudo nano /etc/ssh/sshd_config.d/99-hardened.conf
```

Add the following lines to the configuration file, replacing `customSshPort` with the actual numerical port you defined in the variables section:

```bash
Port customSshPort
PermitRootLogin no
PubkeyAuthentication yes
```

*Note: Ensure you write `Port ` followed directly by your chosen port number (e.g., `Port 2222`).*

Save the file (Ctrl+O, Enter) and exit the text editor (Ctrl+X).

*✔ Verification:* Verify that your configuration contains the correct rules by printing its contents:
```bash
cat /etc/ssh/sshd_config.d/99-hardened.conf
```
Ensure the output lists the chosen port number and `PermitRootLogin no`.

### Step 6: Validate configuration syntax and restart the SSH service

Before applying your changes, run a syntax verification check on the configuration. This prevents getting locked out of the service due to typos.

Execute the validation check:

```bash
sudo sshd -t
```

If there are syntax errors, this command will display them. If no errors are present, the command returns zero output.

Now restart the SSH service to bind to the new custom port:

```bash
sudo systemctl restart ssh
```

Verify that the daemon is actively listening on your configured `customSshPort` by examining network sockets:

```bash
sudo ss -tulpn | grep sshd
```

**Expected Output:**
LISTEN 0      4096         0.0.0.0:2222       0.0.0.0:*      users:(("sshd",pid=1234,fd=3))
LISTEN 0      4096            [::]:2222          [::]:*      users:(("sshd",pid=1234,fd=4))

*✔ Verification:* Verify that the output of the socket list command shows `sshd` listening on your specific custom port configuration rather than port 22.

## Troubleshooting
**Problem:** Command 'ss -tulpn' does not show SSH listening on the custom port after restart.**Solution:** Check your custom configuration file syntax using 'sudo sshd -t'. Verify that another service is not using the port. Ensure the drop-in directory location is enabled inside the main '/etc/ssh/sshd_config' configuration file (look for 'Include /etc/ssh/sshd_config.d/*.conf').**Problem:** Connection refused when attempting loopback test over custom SSH port.**Solution:** Ensure that the UFW firewall (if active) is not blocking traffic on the new port. Test this by running 'sudo ufw allow customSshPort/tcp' and then restarting the SSH service.**Problem:** Name resolution fails ('Temporary failure in name resolution') during ping verification step.**Solution:** Verify system DNS configurations inside '/etc/resolv.conf'. If on a local virtual machine, ensure the host system is connected to the internet and the VM's virtual network interface card (NIC) is enabled and set to NAT or Bridged mode.
## Challenge Exercise

### Challenge: Advanced SSH Access Restriction (Optional)

Using only the standard SSH configuration directories on Ubuntu 24, restrict system login access so that your specific administrative account can connect to the server via SSH, while another dummy local user account is explicitly blocked from establishing SSH sessions. Ensure your configuration does not disrupt other active security restrictions configured during the main lab procedure.

---

# Lab: Securing Services and Analyzing Log Events on Ubuntu

**Objective:** Enable and configure the UFW firewall, inspect running processes, terminate unwanted behaviors, and query system logs using Journald.

**Estimated Time:** 30 minutes

**Platform:** Ubuntu 24 VM (accessed via Windows host or local hypervisor)

**Prerequisites:**
* Access to a local or remote Ubuntu 24 instance with sudo privileges.
* A terminal emulator on your host machine to connect to the Ubuntu instance.

## Procedures

### Step 1: Launch and monitor a simulated long-running background process

In this step, you will start a simulated long-running background process to mimic an unauthorized or runaway service, and then use system monitoring tools to locate it.

* Open your terminal and connect to your Ubuntu 24 system.

Start a background process that executes a long sleep state:

```bash
sleep 3600 &
```

View your active terminal background jobs to verify it is running:

```bash
jobs
```

Search the active process list to find the Process ID (PID) of your `sleep` command using `ps` and `grep`:

```bash
ps aux | grep sleep
```

*Note: Observe the process columns to identify the PID (typically the second column) and the parent process association.*

**Expected Output:**
An active background job list indicating `[1]+ Running sleep 3600 &`, followed by a filtered `ps` list showing the PID of the running `sleep 3600` process.

*✔ Verification:* Confirm that the `ps aux | grep sleep` output contains a line representing the `sleep 3600` process with a unique numerical PID, separate from the `grep` command itself.

### Step 2: Terminate the rogue process using process signals

In this step, you will send signaling terminations to shut down the background process gracefully using its PID.

Using the PID identified in Step 1 (for example, `1234`), send a standard `SIGTERM` (Signal 15) to request a graceful shutdown:

```bash
kill -15 
```

*Replace `` with the actual Process ID discovered in Step 1 (do not include the brackets).* 
Check if the process has terminated:

```bash
ps aux | grep sleep
```

If a process does not respond to standard termination signals, you can force-kill it. Run a new sleep process, locate its PID, and force-kill it with a `SIGKILL` (Signal 9):

```bash
sleep 1800 &
# Note the new PID from the output
kill -9 
```

**Expected Output:**
The shell will notify you that the job has been terminated or killed. A subsequent `ps aux` search for `sleep` will only return the active `grep` filter process.

*✔ Verification:* Verify that `ps aux | grep sleep` no longer lists the active `sleep 3600` or `sleep 1800` processes.

### Step 3: Configure default Uncomplicated Firewall (UFW) policies

In this step, you will initialize and set default traffic rules for your host-level firewall using UFW to block unrequested incoming connections while preserving outbound access.

Check the current status of UFW:

```bash
sudo ufw status
```

Set the default incoming policy to deny all traffic:

```bash
sudo ufw default deny incoming
```

Set the default outgoing policy to allow all traffic:

```bash
sudo ufw default allow outgoing
```

Explicitly allow inbound SSH traffic (Port 22) so you do not lock yourself out of your administrative session:

```bash
sudo ufw allow 22/tcp
```

**Expected Output:**
Output showing:

* Status: inactive (initially)

* Default incoming policy changed to &#39;deny&#39;

* Default outgoing policy changed to &#39;allow&#39;

* Rules updated for port 22/tcp

*✔ Verification:* Confirm that each policy change command returns a success confirmation message in the terminal.

### Step 4: Apply and activate customized firewall rules

Now you will enable the firewall, add a custom service port labeled with your initials, and audit the state of active policies.

Enable the UFW firewall ruleset. Press `y` and then `Enter` when warned that the command may disrupt existing SSH connections:

```bash
sudo ufw enable
```

Add a customized ruleset targeting standard HTTP (Port 80) and a custom port (Port 8080) for a simulated web dashboard, associating the rule with your variable label:

```bash
sudo ufw allow 80/tcp
sudo ufw allow 8080/tcp comment &#39;Web port for learner-${learnerInitials}&#39;
```

Check the detailed status of the active firewall ruleset:

```bash
sudo ufw status verbose
```

**Expected Output:**
Firewall is active and enabled on system startup
Status: active
To                         Action      From

22/tcp                     ALLOW IN    Anywhere
80/tcp                     ALLOW IN    Anywhere
8080/tcp                   ALLOW IN    Anywhere             # Web port for learner-

*✔ Verification:* Confirm from the `sudo ufw status verbose` output that the rules for Port 22, 80, and 8080 are listed as active, and that the comment includes your specific initials.

### Step 5: Query central logs via journalctl to audit service status and firewall actions

In this step, you will inspect central logs via the systemd journal framework to confirm the activity of UFW and audit security changes.

Query the systemd journal specifically for events related to the `ufw` logging tags:

```bash
sudo journalctl -g UFW --no-pager -n 15
```

Filter journal logs from the current boot cycle with warning or higher severity levels to search for general platform administrative faults:

```bash
sudo journalctl -b -p warning --no-pager
```

Inspect real-time logging updates by tailing the system logs:

```bash
sudo journalctl -f
```

*Press `Ctrl+C` to exit the live logging monitoring loop.*

**Expected Output:**
A list of structured system log entries with timestamped kernels/messages highlighting UFW actions, firewall initialization, or system errors.

*✔ Verification:* Verify that logs containing the string 'UFW' or system status changes are returned without errors from the journald query tools.

## Troubleshooting
**Problem:** SSH connection hangs or disconnects after enabling UFW.**Solution:** Ensure that you ran `sudo ufw allow 22/tcp` before executing `sudo ufw enable`. If locked out, restart the virtual machine or connect via your cloud platform console/hypervisor visual console to run `sudo ufw disable`.**Problem:** The command `ps aux | grep sleep` shows the process, but `kill` returns 'No such process'.**Solution:** You may be trying to kill the temporary `grep sleep` process itself instead of the actual background `sleep` execution. Make sure you target the PID associated with the persistent `sleep 3600` program command.**Problem:** The command `journalctl` returns no entries for UFW.**Solution:** By default, UFW logs to the kernel ring buffer. If no traffic has been blocked or accepted yet, logs may be empty. You can force UFW logging levels higher by running `sudo ufw logging medium` and checking again.
## Challenge Exercise

### Advanced Host Access Filtering and Logging (Optional)

Configure an unguided custom rule to block a specific dummy source IP (e.g., `192.168.254.254`) from accessing any port on your machine. Once configured, locate the rule changes in your system journals without outputting the entire system logs, showing only events matching the blocked destination target IP.

---

# Day 1 Capstone Lab: Edge Sensor Station Provisioning and Security Hardening

**Scenario:** You are tasked with provisioning an automated edge sensor logging station on Ubuntu 24.04 LTS. You must configure storage, local user permissions, service security, and host defense.

**Integrated Modules:** Modules 1, 2, 3, and 4
**Estimated Duration:** 90–120 minutes (Bootcamp format: up to 240 minutes)

### Capstone Deliverables & Verification Checklist

1. **Filesystem & User Provisioning (Module 1):**
   * Create group `sensor_ops` and user `sensor_svc` with interactive bash shell and home directory.
   * Grant `sensor_svc` selective sudo rights for service restarts without password prompts in `/etc/sudoers.d/90-sensor-ops`.

2. **Storage Partitioning & Persistence (Module 2):**
   * Provision a virtual loop disk or dedicated partition formatted with `ext4`.
   * Mount the partition at `/mnt/sensor_data` with permissions `775` owned by `sensor_svc:sensor_ops`.
   * Configure persistent mounting via UUID in `/etc/fstab` and verify with `mount -a`.

3. **Network Configuration & OpenSSH Hardening (Module 3):**
   * Confirm default gateway routing and DNS resolution using `ip route` and `resolvectl status`.
   * Harden OpenSSH daemon in `/etc/ssh/sshd_config.d/hardening.conf` by disabling root login (`PermitRootLogin no`) and restricting allowed users (`AllowUsers student sensor_svc`).

4. **Service Process Control & UFW Host Defense (Module 4):**
   * Launch and monitor background sensor log rotation scripts with `systemd` or `nohup`.
   * Configure Uncomplicated Firewall (`ufw default deny incoming`, `ufw default allow outgoing`).
   * Allow SSH on port 22 and sensor telemetry on designated ports; enable UFW and audit with `ufw status verbose` and `journalctl -u ufw`.

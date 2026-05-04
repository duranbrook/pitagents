# PitAgents Demo Script

**Scenario:** Power steering fluid leak — David Chen's 2018 BMW  
**Roles:** Joe as Technician (iPhone) → Joe as Service Advisor (web)  
**Duration:** ~2–3 minutes

---

## Opening

> *"Hi, this is Joe. I'm going to demo how to use Pit AI as a technician and as a service advisor."*

---

## Part 1: Technician on iPhone

### Action: Log in and open the chat

Open the AutoShop app. Log in as a technician. Tap **Chat**.

> *"Starting from the technician — the technician needs to use their phone to record the issue in the repair shop. Start by logging into the app as a technician, go to Chat, and now you can talk with the tech assistant."*

---

### Action: Attach a photo

Tap the camera icon. Take a photo of the power steering fluid reservoir (or select the pre-saved photo from the photo library).

> *"First of all, take a photo of the power steering fluid. Right now I'm just taking a photo — I pull it from the web."*

---

### Action: Send a voice message

Tap the microphone. Speak the following, then tap send:

> *"Hi, I found that the power steering fluid is leaking heavily, and this is for David Chen's 2018 BMW. Can you generate an auto quote for it?"*

---

### Action: Wait for the report

The AI processes the photo and voice message. Wait a few seconds.

> *"We'll send this message and give it a couple of seconds, and then it will return back the auto quote."*

**While waiting, add this aside:**

> *"And actually — you don't need to tell the agent the customer name or the car details manually. You can just scan the VIN number, and the system figures out everything about the vehicle automatically."*

---

### Action: The AI flags the photo (expected — happens in the response)

The AI's response comes back. As part of its reply, it flags that the photo appears to be sourced from the web rather than taken on-site, and asks for a real photo.

> *"Notice — the AI actually caught that. It identified that this photo is from a web page, not a real photo taken in the shop, and it's asking me for the real one."*

Respond in the chat:

> *"Let's treat it as a real photo for now. This is for demo purposes."*

The AI acknowledges and proceeds. The report card appears with a link to the estimate page.

---

### Action: Modify pricing and message

Tap the report link. The estimate web page opens.

> *"Once the auto quote is returned, you will see a web page where you can modify the pricing and the message."*

Edit the labor rate or line items. Update any notes in the message field.

---

### Action: Regenerate the PDF

Tap **Regenerate PDF**.

> *"Once the pricing and message are finalized, click Regenerate PDF."*

The PDF opens in the mobile app as the finalized site report.

> *"This is the finalized report that will be delivered to the service advisor."*

---

## Part 2: Service Advisor on Web

### Action: Open the web dashboard

Switch to the laptop. The service advisor web dashboard is open.

> *"Now let's go to the web page. You can use it the traditional way — clicking, typing, chatting with the agent — and you can also talk with the web using your voice."*

> *"Let's demo that."*

---

### Voice navigation sequence

Speak each command, pause for the UI to respond, then continue:

1. > *"Can you go to the Chats app?"*

   The UI navigates to the chat section.

2. > *"Can you go to the Customers tab?"*

   The customers list appears.

3. > *"Can you select David Chen?"*

   David Chen's profile opens.

4. > *"Can you select the 2018 BMW?"*

   The vehicle is selected.

5. > *"Can you select his report?"*

   The finalized repair report opens on screen.

---

### Action: Share with the customer

> *"Boom! Now the service advisor can share this report with consumers."*

Tap **Share** or copy the report link to send to the customer.

---

## Demo Checklist

- [ ] App login works for technician account
- [ ] Photo attaches and uploads in chat
- [ ] Voice message transcribes correctly
- [ ] AI returns auto quote within ~10 seconds
- [ ] Report link opens the estimate web page
- [ ] Pricing and message edits are saved
- [ ] Regenerate PDF produces the updated report
- [ ] Web dashboard: voice command "go to Chats app" navigates correctly
- [ ] Web dashboard: voice command "go to Customers tab" works
- [ ] Web dashboard: "select David Chen" finds and opens the customer
- [ ] Web dashboard: "select the 2018 BMW" selects the vehicle
- [ ] Web dashboard: "select his report" opens the finalized report
- [ ] Share / copy link works for customer delivery

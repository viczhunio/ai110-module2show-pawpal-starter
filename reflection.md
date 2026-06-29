# PawPal+ Project Reflection

## 1. System Design                       

**Core Actions**            
                       
Three core actions include managing multiple pets, adding time availability, and scheduling tasks like walking or feedings.                          

**a. Initial design**                       

- Briefly describe your initial UML design.       

The initial design connects User to their pets. It handles everything the pet needs (walks, grooming, meds, feedings), creating a template called CareEvent. All events have basic tracking details for time and priority. ScheduleManager takes the owner's availability limits and builds a DailyPlan to fit their schedule. 

- What classes did you include, and what responsibilities did you assign to each?    

A User Class trackes the owner's profile/information and pets they own. The Pet Class stores the pet's information and keeps track of all tasks scheduled for that pet. The CareEvent Class holds details that tasks share like the time, how long it takes and how important it is, as well as if it's been completed or not. The Walk Class is a special CareEvent and adds specific dog-walking details like route and distance. Constraints Class holds the owner's boundaries/limits such as their availability and preferences. ScheduleManager Class looks at all needed tasks and compares them with owner availibilty and sorts them logically. Daily Plan Class holds the final output, it lists all finalized, ordered tasks and explains why the plan was built that way. 



**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.        

Yes, the biggest change was splitting a single task into two, CareTask describing recurring care and CareEvent that represents one specific occurrence on a given day. This change was made because the original design used one class for recurring events and individual scheduled task, such as "feed daily" and "this morning's feeding, completed" would have been under one object. Separating kept recurring tasks and daily schedule clean. 


---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?   
            
The scheduler considers calendar dates, available time, task importance, and user choices. It checks the calendar to see if a task is due that day and checks if the task is a single day or multiple days. Next the calendar considers the total time the owner has to spend on pet care that day. The daily time limit was an important constraint because the owner can't find extra time in a 24 hour day. It's more of a physical limit so tasks should be organized within that, by priority, etc. The scheduler filters and prioritizes more important tasks. 


**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?    
       
One tradeoff the scheduler makes is that inside _resolve_conflicts, instead of computing every mathematical combination to maximize total daily minute utilization, the algorithm ranks the active tasks by their score. It processes the score sequentially and then discards any event that causes a time-window overlap with a previously accepted task or pushes the total schedule over the owner's daily time limit.      
          
This tradeoff is reasonable because it prioritizes computational efficiency and system predictability over theoretical precision. This makes the pet care app speedy and helpful over prioritizing perfect math. Running the optimization routine usees O(N log N) sorting time which prevents excessive battery drain and scaling to multi-pet households. If the scheduler used a complex mathematical solver to rearrange the day, it would make it harder for the app to display a single written note explainin the choices it made for the daily plan.    
                 
---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

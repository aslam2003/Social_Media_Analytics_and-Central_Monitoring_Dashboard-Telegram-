from telethon import TelegramClient, errors
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto,Channel,User,UserStatusOffline,UserStatusOnline
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.users import GetFullUserRequest
import pytz
import asyncio
from pymongo import MongoClient
from datetime import date,datetime,timedelta
import time 
import nltk
from nltk.corpus import stopwords
import os
from flask import Flask,render_template,request,flash,session,redirect,url_for
nltk.download('stopwords')
date_today = date.today().strftime("%d-%m-%Y")#Today's date
timezone = pytz.timezone("Asia/Kolkata")#Indian Timezone
nltk.download('punkt')
nltk.download('stopwords')
single_letter=[chr(i) for i in range(65,91)]+[chr(i) for i in range(97,123)]
single_nums=[str(i) for i in range(10)]
special_characters=["!@#$%^&*()_+-={}[]:\";'<>?,./\\|`~"]
filterwords=list(stopwords.words('english'))+single_letter+single_nums+special_characters


mongodb_client =MongoClient("mongodb://localhost:27017/")
api_id = 0x0x0x0x0x
api_hash = "***************************"
message_database = mongodb_client["channel_database"]#Database about messages of channels
scraping_database = mongodb_client["scraping_database"]#Database for scraping status of messages from channel
message_collection = message_database["Message_Collection"]#Channels in a message
scraping_collection = scraping_database["Scrapping_status"]#Status of each Channel
users_collection = message_database["User_Details"]#User details 
messagedaycount_collection=message_database["MessageCountPerDayCollection"]#Count of messages scraped per day
usercountcollection=message_database["UserCountCollection"]#User participation history
filteredmessages=message_database["FilteredMessages"]
keywords_collection=message_database['Keywords']
unparliamentary_collection=message_database["unparliamentary_words_in_messages"]
daywise_unparliamentarywords=message_database["daywiseunparliamentarywords"]
frequent_words=message_database["FrequentWords"]
reply_messages=message_database["ReplyMessages"]
authentication_database=mongodb_client["Authentication_Details"]
credentials_collection=authentication_database["Credentials"]
unparliamentary_keywords=message_database["Unparliamentary_Words"]



keywords=list(keywords_collection.find({},{"_id":0,"Keywords":1}))
options={
          "option1":keywords[0]["Keywords"],
          "option2":keywords[1]["Keywords"],
          "option3":keywords[2]["Keywords"],
          "option4":keywords[3]["Keywords"]
        } 

unparliamentary_words=["abused","ashamed","ballarat","baloney","batshit crazy","beaten with shoes",
                       "betrayal","betrayed","bikies","bloodshed","bloody","bossy pants","bullshit",
                       "chamacha","chamachagiri","cheat","cheated","chelas","childishness","chhokra","circumeventing",
                       "closeau","cockroaches","conversion","conversions","corrupt","corruption","coward","covid spreader",
                       "criminal","crock","crococodile tears","cruel","debacle","decieved","derogatory","disgrace",
                       "dogdy","dog","donkey","drama","dump","duplicity","erroneous","eyewash","fake","false","fabrication",
                       "fool","foolish","fraud","frighten","gag","gaslighting","goons","goose","gossipers","greasy","greed","groper",
                       "grubby","gun","gundas","hack","heckler","hooliganism","humiliated","hunter","hypocrisy","hypocrite","ignores",
                       "ignores","illegally","incompetent","interjecting","irresponsible","jack-all","jumble jim","kick out","liar","lie",
                       "lollipops","looting","mafia","mamas","mate","menzies","mess","misaligned","misinformation","mislead","murder","negligence","ophidian",
                       "paedophiles","partisan","penguin","petdog","phoney","pig-headed","poster-boy","prostitute",
                       "pyschiatrist","racist","rankin","rape","rascal","recalcitrant","ridicule","rort",
                       "rowdy","rubbish","rudd","ruthless","saleswoman","sanctimonious","scammed","scandal","scoundrel",
                       "shame","shit","shorts culture","show off","slapping","slush fund","snake charmers","snoopgate",
                       "species","stench","stuff up","stuffed","stupidity","suck","theft","touts","traitor","treacherous","untrue",
                       "weasel words","whippet","wicked","windbag","witch","worst","yapping"]

filepath="C:\\Users\\Lenovo\\Desktop\\Messages.txt"

app=Flask(__name__)
app.secret_key="secret12@3$%^"

def filewrite(information):
    with open(filepath,'a',encoding='utf-8')as file:
        file.write("Channel Name: "+ information["Channel Name"])
        file.write("\nText Message: "+ information["Text"])
        file.write("\nKeyword Used: "+  str(information["Keyword"]))
        file.write("\nCount: "+str(information["Count"]))
        file.write("\nUser_ID: "+ str(information["User_ID"]))
        file.write("\nTime Updated: "+str(date_today))
        file.write( "\n\n")




@app.route("/", methods=["GET", "POST"])
def authentication():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        user_details = credentials_collection.find_one({"Username": username})
        
        if user_details:
            role = user_details["Role"]
            registered_password = user_details["Password"]
            
            if password == registered_password:
                return render_template('sections.html', user_details=user_details)
            else:
                flash("Password invalid!")
                return render_template('Authentication.html')
        else:
            flash("User not found")
            return render_template('Authentication.html')
    else:   
         return render_template("Authentication.html")

    

@app.route("/add_credentials",methods=["GET","POST"])
def add_credentials():
    if request.method=="POST":
        username=request.form['username']
        password=request.form['password']
        role=request.form['role']
        flag=credentials_collection.find_one({"Password":password,"Username":username,"Role":role})
        if flag:
            flash("User already exists")
            return render_template("Credentials.html")
        else:
            credentials_collection.insert_one({"Username":username,"Password":password,"Role":role})
            flash("User Details Entered")
            return render_template("Credentials.html")
    else:
        return render_template("Credentials.html")
    

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":   
       phone_number=request.form['phone']
       channel=request.form['channel']
       timeoption=request.form['time']
       duration=request.form['subTime']           
       session['phone_number']=phone_number
       session['channel_name']=channel
       session['time_option']=timeoption
       session['duration']=duration
       return redirect(url_for("add_channel"))
    else:
        return render_template("login.html")

@app.route("/addchannel",methods=["GET","POST"])
async def add_channel(): 
    telegram_client = TelegramClient("new_test_client_1", api_id, api_hash)
    await telegram_client.connect()
    try:
        if not await telegram_client.is_user_authorized():
            await telegram_client.send_code_request(phone=session['phone_number'])
    except Exception as e:
        flash(str(e),"error")
        return redirect(request.url)
    
    if request.method=="POST":             
        login_code=request.form["login_code"]  
        two_factor_password=request.form["two_factor_password"]
        
        try:
            await telegram_client.sign_in(session["phone_number"],login_code)
        except errors.SessionPasswordNeededError:
            await telegram_client.sign_in(password=two_factor_password)           
        
        flash("Login Successful!", "message") 
        flash("Scraping Started!")

        channel_entity=session["channel_name"]
        channel_information = await telegram_client.get_entity(channel_entity)
        channel_id = int("-100" + str(channel_information.id))

        my_user=await telegram_client.get_me()
        my_user_id=my_user.id

            #Channel Information
        full_channel = await telegram_client(GetFullChannelRequest(channel_entity))
        userscount = full_channel.full_chat.participants_count
        description = full_channel.full_chat.about 
        channel_username=full_channel.chats[0].username
        channel_accesshash=full_channel.chats[0].access_hash
        admin_count=full_channel.full_chat.admins_count
        kicked_count=full_channel.full_chat.kicked_count
        banned_count=full_channel.full_chat.banned_count
        linked_chat_id=full_channel.full_chat.linked_chat_id
        linked_chat_entity=await telegram_client.get_entity(linked_chat_id) if linked_chat_id is not None else None
        linked_chat_title=linked_chat_entity.title if linked_chat_id is not None else None
        linked_chat_type="Private Chat" if linked_chat_entity is not None and isinstance(linked_chat_entity,User) else "Group/Channel" if linked_chat_entity is not None and isinstance(linked_chat_entity,Channel) else "Unknown Type"
        megagroup=full_channel.chats[0].megagroup
        gigagroup=full_channel.chats[0].gigagroup
        verified=full_channel.chats[0].verified
        restriction_reasons=full_channel.chats[0].restriction_reason
        if description == "":
            description="No  Description Provided."
        print("Channel ID:", channel_id)
        print("Query Entered")
        query ={"Channel Name": channel_entity}
        result_scrape = scraping_collection.find_one(query)
        message_id = 1
        if not result_scrape:
            scraping_collection.insert_one(
                {
                "Channel Name": channel_entity,
                "Channel Description": description,
                "Channel_Access_Hash":channel_accesshash,
                "Channel_Usename":channel_username,
                "Start_date": date_today,
                "Recent_Date": date_today,
                "Number of Users": userscount,
                "Admin_Count":admin_count ,
                "Kicked_Count":kicked_count,
                "Banned_Count":banned_count,
                "Linked Chat Title":linked_chat_title,
                "Linked_Chat_Type":linked_chat_type,
                "Megagroup":megagroup,
                "Gigagroup":gigagroup,
                "Verified":verified,
                "Restriction_reasons":restriction_reasons,
                "Status": True,
            }
        )
            print("new Channel is inserted")
        else  :
            if (result_scrape['Status'] == False):
                flash("Status is set False for the channel")
                return render_template('form.html')
            
            else:
                newvalues = {
                            "$set": {"Channel Description": description,
                            "Channel_Access_Hash":channel_accesshash,
                            "Channel_Username":channel_username,
                            "Recent_Date": date_today, 
                            "Number of Users": userscount,
                            "Admin_Count":admin_count ,
                            "Kicked_Count":kicked_count,
                            "Banned_Count":banned_count,
                            "Megagroup":megagroup,
                            "Gigagroup":gigagroup,
                            "Verified":verified,
                        "Restriction_reasons":restriction_reasons}
                    }
                scraping_collection.update_one(query, newvalues)
            
        result_message = message_collection.find_one(query)
        if result_message:
            result = (
                    message_collection.find({"Channel Name": channel_entity})
                    .sort("Message_ID", -1)
                    .limit(1)
                    )
            message_id = (
                    result[0]["Message_ID"]
                    if message_collection.count_documents(query) > 0
                    else None
                    )
            print("Maximum message id found:", message_id)
        #Setting time for scheduling scraping of messages
        current_time=datetime.now()
        if(session["time_option"]=="hours"):
            hours=int(session["duration"])
            schedule_duration=timedelta(hours=hours)
            schedule_time=current_time+schedule_duration
            print(schedule_time)
        elif(session["time_option"]=="minutes"):
            mins=int(session["duration"])
            schedule_duration=timedelta(minutes=mins)
            schedule_time=current_time+schedule_duration
            print(schedule_time)
        else:
            seconds=int(session["duration"])
            schedule_duration=timedelta(seconds=seconds)
            schedule_time=current_time+schedule_duration
            print(schedule_time)

        user_id = None
        username = None

        message_scraping_count:int=0
        cycles=0

        unparliamentary_matched_words=[]
        async for message in telegram_client.iter_messages(
                channel_id,min_id=message_id, reverse=True
            ):
                
            current_time=datetime.now()
            if current_time>schedule_time:
                schedule_time= schedule_time+schedule_duration
                cycles+=1
                print(cycles)
                if cycles==2:#Decrementing scraping count when the message is not scraped
                    break
            if message.from_id is not None:
                user_id = message.from_id.user_id
                try:
                    user = await telegram_client.get_entity(user_id)
                    if hasattr(user, "username"):
                        username = user.username
                except (AttributeError,ValueError):
                        username=None
                except errors.FloodWaitError as e:
                    print(f'Rate limit exceeded. Waiting for {e.seconds} seconds.')
                    await asyncio.sleep(e.seconds)
                    user = await telegram_client.get_entity(user_id)

                              
            message_scraping_count+=1
            localized_time = message.date.astimezone(timezone)
            formatted_time = localized_time.strftime("%d-%m-%Y %H:%M:%S")
  
            if message.media:
                if isinstance(message.media, MessageMediaDocument):
                    mime_type = message.media.document.mime_type.lower()
                    if "audio" in mime_type:
                        #Checking if message is of audio type
                        downloaded_audio = await telegram_client.download_media(
                            message.media,
                            file="C:\\Users\\Lenovo\\Desktop\\CDAC\\Audios",
                        )
                        audio_filename = os.path.basename(downloaded_audio)
                        message_collection.insert_one(
                            {
                                "Channel Name": channel_entity,
                                "Message_ID": message.id,
                                "User ID": user_id,
                                "Username": username,
                                "Type": "Audio",
                                "Local_file_path": "Audios" + "/" + audio_filename,
                                "URL": str("https://t.me/")
                                + channel_entity
                                + "/"
                                + str(message.id),
                                "Date and Time": formatted_time
                            }
                        )
                        time.sleep(0.01)
                    elif "video" in mime_type:
                        #Checking if message is of video type
                        downloaded_video = await telegram_client.download_media(
                            message.media,
                            file="C:\\Users\\Lenovo\\Desktop\\CDAC\\Videos",
                        )
                        video_filename = os.path.basename(downloaded_video)
                        message_collection.insert_one(
                            {
                                "Channel Name": channel_entity,
                                "Message_ID": message.id,
                                "User ID": user_id,
                                "Username": username,
                                "Type": "Video",
                                "Local_file_path": "Videos" + "/" + video_filename,
                                "URL": str("https://t.me/")
                                + channel_entity
                                + "/"
                                + str(message.id),
                                "Date and Time": formatted_time
                            }
                        )
                        time.sleep(0.01)

                elif isinstance(message.media, MessageMediaPhoto):
                    #Checking if message is of photo type
                    downloaded_photo = await telegram_client.download_media(
                        message.media,
                        file="C:\\Users\\Lenovo\\Desktop\\CDAC\\Images",
                    )
                    photo_filename = os.path.basename(downloaded_photo)
                    message_collection.insert_one(
                        {
                            "Channel Name": channel_entity,
                            "Message_ID": message.id,
                            "User ID": user_id,
                            "Username": username,
                            "Type": "Photo",
                            "Local_file_path": "Images" + "/" + photo_filename,
                            "URL": str("https://t.me/")
                            + channel_entity
                            + "/"
                            + str(message.id),
                            "Date and Time": formatted_time
                        }
                    )
                    time.sleep(0.01)

            else:
                #Message is of type text
                message_collection.insert_one(
                    {
                        "Channel Name": channel_entity,
                        "User ID": user_id,
                        "Username": username,
                        "Message_ID": message.id,
                        "Type": "Text",
                        "Text_message": message.text.lower() if message.text is not None else None,
                        "Date and Time": formatted_time
                    }
                )
                #Checking for unparliamentary words in a text message
            text_message=message.text.lower().split() if message.text is not None else None
            occurence=0
            if text_message:
              for word in text_message:
                if word in unparliamentary_words:
                    unparliamentary_matched_words.append(word)
                
                for option in options:
                    for keyword in option:
                        if keyword in word and occurence<1:
                            #Send the unparliamentary messages to a specific channels
                            await telegram_client.send_message(-010800243,message)
                            occurence+=1
                            break


            time.sleep(0.01)
            #Checking for action sent to messages
            action_taken='No'
            if message.reply_to_msg_id is not None :
                action_taken='Yes'
                original_message=await telegram_client.get_messages(channel_id,ids=message.reply_to_msg_id)
                original_message_userid=original_message.from_id.user_id  
                if original_message_userid==my_user_id:
                    original_sender_username= original_message.sender.username if original_message.sender else 'N/A'
                    original_message_time=original_message.date.astimezone(timezone).strftime("%Y-%m-%d  %H:%M:%S")
                    if original_message.media:
                        if isinstance(message.media,MessageMediaPhoto):
                            original_text="The message is a photo.The photo is downloaded at Photos folder"   
                            Message_Type="Photo"
                        elif isinstance(message.media,MessageMediaDocument):
                            mime_type = message.media.document.mime_type.lower()
                            if "audio" in mime_type: 
                                original_text="The message is an audio.The audio is downloaded at Audios folder" 
                                Message_Type="Audio" 
                            elif "video" in mime_type:
                                original_text="The message is a video.The video is downloaded at Videos folder"
                                Message_Type="Video"
                    else:
                            original_text=message.text
                            Message_Type='Text'
                    if message.media:
                        if isinstance(message.media,MessageMediaPhoto):
                            reply_text="The reply is a photo.The photo is downloaded at Photos folder"   
                            Type="Photo" 
                        elif isinstance(message.media,MessageMediaDocument):
                            mime_type = message.media.document.mime_type.lower()
                            if "audio" in mime_type: 
                                reply_text="The reply is an audio.The audio is downloaded at Audios folder" 
                                Type="Audio" 
                            elif "video" in mime_type:
                                reply_text="The reply is a video.The video is downloaded at Videos folder"
                                Type="Video"
                    else:
                        reply_text=message.text
                        Type='Text'
                    reply_messages.insert_one({"Channel Name":channel_entity,
                        "Message":original_text,
                        "Message ID":message.reply_to_msg_id,
                        "User_ID":original_message_userid,
                        "Username":original_sender_username,
                        "Origin Time":original_message_time,
                        "Message_Type":Message_Type,
                        "Action":action_taken,
                        "Reply":reply_text,
                        "Reply Message ID":message.id,
                        "Reply_User_ID":user_id,
                        "Reply_Username":username,
                        "Reply_Type":Type,
                        "Reply Time":formatted_time}) 

        #Getting information about participants of a channel if we are             
        try: 
            async for participant in telegram_client.iter_participants(channel_entity):
                participant_info=await telegram_client(GetFullUserRequest(participant))    
                participant_id=participant_info.full_user.id
                participant_entity=await telegram_client.get_entity(participant_id)
                participant_username=participant_info.users[0].username
                participant_firstname=participant_info.users[0].first_name
                participant_lastname=participant_info.users[0].last_name
                participant_accesshash=participant_info.users[0].access_hash
                participant_bio=participant_info.full_user.about
                participant_status=participant_info.users[0].status
                status_type="Recently"
                status_date=None
                if isinstance(participant_status,UserStatusOffline):
                    recent_status=participant_status.was_online
                    status_date=recent_status.astimezone(timezone).strftime("%d-%m-%Y  %H:%M:%S")
                    status_type="Online" 
                elif isinstance(participant_status,UserStatusOnline):
                    recent_status=participant_status.expires
                    status_date=recent_status.astimezone(timezone).strftime("%d-%m-%Y  %H:%M:%S")
                    status_type="Offline"
        
            profile_photo_path=None
            if participant_info.full_user.profile_photo:
                profile_photo=await telegram_client.download_profile_photo(participant_entity,file="C:\\Users\\Lenovo\\Desktop\\CDAC\\static\\User_Images")
                profile_photo_path=os.path.basename(profile_photo)
                users_record = users_collection.find_one({"User_ID":participant_id})
            if users_record:
                channelgroups = users_record.get("Channels",[])
                if channel_entity not in channelgroups:
                   updatedvalues = {
                        "$addToSet": {"Channels":channel_entity},
                        "$set":{"FirstName" : participant_firstname,
                                "LastName":participant_lastname,
                                "LastName":participant_lastname,
                                "Bio":participant_bio,
                                "Status":status_date,
                                "Profile Photo Path":profile_photo_path
                        }
                }
                   users_collection.update_one(
                    {"User_ID":participant_id}, updatedvalues
                            )
            else:
                users_collection.insert_one({
                    "User_ID":participant_id,
                    "UserName":participant_username,
                    "FirstName":participant_firstname,
                    "LastName":participant_lastname,
                    "Bio":participant_bio,
                    "AccessHash":participant_accesshash,
                    "Status Type":status_type,
                    "Status":status_date,
                    "Profile Photo Path":profile_photo_path,
                    "Channels":[channel_entity]
                    
                })
        except errors.ChatAdminRequiredError:
            flash("Not possible to retrieve informations of participants due to admin privileges")

        flash("Scraping finished!.Analysis started don't move to other pages")  

        messagecount=message_collection.count_documents({"Channel Name":channel_entity})
        newvalues={"$set":{"Count":messagecount}}
        scraping_collection.update_one(query,newvalues)
        flag=messagedaycount_collection.find_one({"Channel Name":channel_entity,"Day":date_today})
        totalcountchecker=scraping_collection.find_one({"Channel Name":channel_entity})
        if flag:
            past_count=flag["Count"]
            total_count=message_scraping_count+past_count
            #If no new messages are not scraped then do not need to update today's count
            if total_count<totalcountchecker["Count"]:
                newvalues={"$set":{"Count":total_count}}
                messagedaycount_collection.update_one(query,newvalues)
        else:
            messagedaycount_collection.insert_one({"Channel Name":channel_entity,"Day":date_today,"Count":message_scraping_count})    
        pipeline = [
        {"$unwind": "$Channels"},
        {"$group": {"_id": "$User_ID", "channel_count": {"$sum": 1},"channels": {"$push": "$Channels"}}},
        {"$sort": {"channel_count": -1}},
        {"$limit": 10},
        {"$lookup": {
        "from": "User_Details",
        "localField": "_id",
        "foreignField": "User_ID",
        "as": "user_info"
        }},
        {"$project": {
        "_id": 1,
        "username": {"$arrayElemAt": ["$user_info.UserName", 0]},
        "profile_photo_path": {
        "$cond": {
        "if": {"$eq": [{"$arrayElemAt": ["$user_info.Local Path", 0]}, "N/A"]},
        "then": "No Photo Available",
        "else": {"$arrayElemAt": ["$user_info.Local Path", 0]}    
        }
        },
        "channels":1,
        "channel_count": 1  
        }}
        ]
        usercountcollection.delete_many({})
        results=list(users_collection.aggregate(pipeline))
        usercountcollection.insert_many(results)
        message_collection.create_index([('Text_message','text')])
    
        matched_keywords=[]
        for option in options:
            keywords=options[option]
            keywords_query=" ".join(keywords)
            matchedkeywordsmessages=message_collection.find({"$text":{"$search":keywords_query}},{"_id":0})
    
        #Count of same spam messsages being sent by the same user
        for document in matchedkeywordsmessages:
            filter_query={"Channel Name":document["Channel Name"],"Text":document["Text_message"],"User_ID":document["User ID"]}
            count=filteredmessages.count_documents(filter_query)
            flag=filteredmessages.find_one(filter_query)
            if flag:
            #Checking if the message is already filtered,if yes no need to perform any changes
                newcount={"$set":{"Count":count}}
                filteredmessages.update_one(filter_query,newcount)
                filewrite(flag)
            else:
                count=1
                matched_keywords=[keyword for keyword in keywords if keyword in document["Text_message"]]
                filteredmessages.insert_one({"Channel Name":document["Channel Name"],"Text":document["Text_message"],"Keyword":matched_keywords,"Option":option,"Count":count,"User_ID":document["User ID"],"Username":document["Username"]})
                flag=filteredmessages.find_one(filter_query)
                filewrite(flag)
            matched_keywords.clear()
        

        pipeline = [
            {"$match": {"Channel Name": channel_entity, "Type": "Text","Text_message": {"$ne": None}}},
            {"$project": {
            "words": {
            "$filter": {
            "input": {
                "$split": [
            {
                    "$trim": {
                        "input": {
                            "$replaceAll": {
                                "input": {"$toLower": "$Text_message"},
                                "find": "[\\s-!.]+", # Matches spaces, hyphens, exclamation marks, and full stops
                                "replacement": " "
                            }
                        }
                    }
                },
                " "
            ]
        },
                "as": "word",
            "cond": {
            "$and": [
                {"$not": {"$in": ["$$word", filterwords]}}, # Exclude stopwords
                {"$ne": ["$$word", "\n"]} # Exclude empty strings (newlines)
            ]
        }
    }
}
}},
            {"$unwind": "$words"},
            {"$group": {"_id": {"word": "$words"}, "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5},
        ]
    
        results=message_collection.aggregate(pipeline)
        words=[]
        for result in results:
            words = result["_id"]["word"]
            count=result["count"]
            flag=frequent_words.find_one({"Channel Name":channel_entity})
            word_pair={words:count}
            if not flag :
                frequent_words.insert_one({"Channel Name":channel_entity,"Word":[word_pair]})
            else:
              newvalues={"$addToSet":{"Word":word_pair}}
              frequent_words.update_one({"Channel Name":channel_entity},newvalues)        
                
        #Unparliamentary words
        flag=unparliamentary_collection.find_one({"Channel Name":channel_entity,"Day":date_today})
        if not flag :
           unparliamentary_collection.insert_one({"Channel Name":channel_entity,"Words":unparliamentary_matched_words,"Day":date_today,"Count":len(unparliamentary_matched_words)})
        
        flash("Scraping Completed")
        #Getting channel details
        channel_name=session['channel_name']
        channel_entity=await telegram_client.get_entity(channel_name)
        channel_id=channel_entity.id
        channel_details=scraping_collection.find_one({"Channel Name":channel_name},{"id_":0})

        
        #Retrieving all messages
        
        #Logging out
        await telegram_client.log_out()
        return render_template("form.html",channel_details=channel_details)
    else:
        return render_template("form.html",channel_details=None,history_messages=None) 

    
    
    
    

@app.route("/analysis",methods=["GET","POST"])
def analysis():
     
     #Defining sort order by clicking on column headers
    sort_field = request.args.get('sort_field', 'Channel Name')
    sort_order = int(request.args.get('sort_order', 1))
    table_id = request.args.get('table_id', 'table1')
    channeldetails1 = list(scraping_collection.find().sort(sort_field, sort_order))
    message_daily_count1 = list(messagedaycount_collection.find().sort(sort_field,sort_order))

    messagesperdaydocuments=messagedaycount_collection.find({},{"_id":0})
    topuserdocuments=usercountcollection.find({})
    keywords_documents=keywords_collection.find({},{"_id":0})
    frequent_words_documents=frequent_words.find({},{"_id":0})
    unparliamentary_collection_documents=unparliamentary_collection.find({},{"_id":0})
    reply_messages_collection=reply_messages.find({},{"_id":0})

    messagesperdaydocumentslist=[document for document in messagesperdaydocuments]
    topuserdocumentslist=[document for document in topuserdocuments]
    keywordsdocumentslist=[document for document in keywords_documents]
    frequent_words_documents_list=[document for document in frequent_words_documents]
    unparliamentary_collection_documents_list= [document for document in unparliamentary_collection_documents ]
    reply_messages_collection_documents_list= [document for document in reply_messages_collection ]

    if table_id == 'table1':
        if sort_field == 'Channel Name':
            collation = {'locale': 'en', 'strength': 2}
            channeldetails1 = list(scraping_collection.find().sort('Channel Name', sort_order).collation(collation))
        else:
            channeldetails1 = list(scraping_collection.find().sort(sort_field, sort_order))
    elif table_id == 'table3':
        if  sort_field == 'Count':  # Adjust field name if necessary
         message_daily_count1 = list(messagedaycount_collection.find().sort(sort_field, sort_order))
    else:
         message_daily_count1 = list(messagedaycount_collection.find())

    if request.method=="POST":
        selected_option=request.form['options']
    
        filtered_documents=filteredmessages.find({"Option":selected_option},{"_id":0})
        filteredmessagesdocuments=[document for document in filtered_documents] 

        return render_template("analysis.html",message_daily_count=message_daily_count1,top_ten_users=topuserdocumentslist,filtered=filteredmessagesdocuments,keywordsdocuments=keywordsdocumentslist,frequentwords=frequent_words_documents_list,unparliamentarywords=unparliamentary_collection_documents_list,replymessages=reply_messages_collection_documents_list,channeldetails=channeldetails1,sort_field=sort_field, sort_order=sort_order, table_id=table_id)
    

    else:        
        return render_template("analysis.html",top_ten_users=topuserdocumentslist,message_daily_count=message_daily_count1,keywordsdocuments=keywordsdocumentslist,frequentwords=frequent_words_documents_list,unparliamentarywords=unparliamentary_collection_documents_list,replymessages=reply_messages_collection_documents_list,channeldetails=channeldetails1,sort_field=sort_field, sort_order=sort_order, table_id=table_id)

@app.route("/keywords",methods=["GET","POST"])
def addKeywords():
     filterwordsdocuments=keywords_collection.find({},{"_id":0})
     unparliamentarywordsdocuments=unparliamentary_keywords.find_one({},{"_id":0})
     if request.method=="POST":
        form_id=request.form['form_id']
        if form_id=='form1':
            option=request.form["options"]
            keyword=request.form["keyword"]
            keyword=keyword.lower()
            flag:None
            if option=="Unauthorised use of Information":    
                query={"Category":"Unauthorised use of Information"}
                flag=keywords_collection.find_one(query)
                
            elif option=="Offensive and inappropriate content":
                query={"Category":"Offensive and inappropriate content"}
                flag=keywords_collection.find_one(query)
            elif option=="Harmful to children":
                query={"Category":"Harmful to children"}
                flag=keywords_collection.find_one(query)
            
            else:
                query={"Category":"Violates intellectual property rights"}
                flag=keywords_collection.find_one(query)
            
            if keyword not in flag["Keywords"]:
                    newentry={"$addToSet":{"Keywords":keyword}}
                    keywords_collection.update_one(query,newentry)


            return render_template("keywords.html",documents=filterwordsdocuments,words=unparliamentarywordsdocuments)     
        else:
            keyword=request.form['keyword']
            query={"Category":"Unparliamentary"}
            flag=unparliamentary_keywords.find_one(query)
            if keyword not in flag["Keywords"]:
                 unparliamentary_keywords.update_one(query,{"$addToSet":{"Keywords":keyword}})
            return render_template("keywords.html",documents=filterwordsdocuments,words=unparliamentarywordsdocuments)
      
     else:
         return render_template("keywords.html",documents=filterwordsdocuments,words=unparliamentarywordsdocuments)
     


        
         
        

async def main():
    # Start the scheduled task in the background
    task1 = asyncio.create_task(app.run(debug=True))

    # Wait for both tasks to complete
    await task1

# Run the main function directly if this script is executed
if __name__ == "__main__":
    asyncio.run(main())



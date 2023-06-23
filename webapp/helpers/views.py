import json

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from webapp import data_manager, db
from webapp.helpers.data_utils import DataManager

from .models import LangAnn, Sequences

views = Blueprint("views", __name__)  # set up blueprint

@views.route("/", methods=["GET", "POST"])
@login_required
def home():
    if request.method == "POST":
        return redirect(url_for("annotator.annotate", user=current_user))
    else:
        if Sequences.query.count() < 1:
            data = data_manager.data
            for info in data:
                start, end = info["indx"][:2]
                start = data_manager.filename_to_idx(start)
                end = data_manager.filename_to_idx(end)
                new_data_point = Sequences(dir=info["dir"],
                                           n_frames=info["n_frames"],
                                           start_frame=start,
                                           end_frame=end,
                                           video_tag=data_manager.video_tags[(start,end)])
                db.session.add(new_data_point)
            db.session.commit()
        return render_template("home.html", user=current_user)


@views.route("/completed")
@login_required
def completed():
    flash("\nData collection completed successfully!\n Congratulations!")
    return render_template("completed.html", user=current_user)

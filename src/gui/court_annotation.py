import json
from tkinter import Canvas, Tk, Button
from PIL import Image, ImageTk
import cv2
import random

from mathutils import Vector
from mathutils.geometry import intersect_point_line
from numpy._typing import NDArray
from typing_extensions import List, Tuple, Dict

from src.ml.yolo.court.segmentation import CourtSegmentor


class CourtAnnotator(object):
    def __init__(self, filename: str):
        self._x = None
        self._y = None
        cfg = {
            'weight': '/home/masoud/Desktop/projects/volleyball_analytics/weights/court_segment/weights/best.pt',
            "labels": {0: 'court'}
        }
        self.segmentor = CourtSegmentor(cfg=cfg)
        self.filename = filename
        self.cap = cv2.VideoCapture(self.filename)
        assert self.cap.isOpened(), "file is not accessible."
        self.w, self.h, self.fps, _, self.n_frames = [int(self.cap.get(i)) for i in range(3, 8)]

        self.size = 20
        self.frame = self.get_frame()
        tl, dl, dr, tr = self.ml_guided_corners(self.frame)

        self.w_tl = tl[0]
        self.w_tr = tr[0]
        self.w_dl = dl[0]
        self.w_dr = dr[0]
        self.h_top = tl[1]
        self.h_down = dr[1]

        self.net_DR = self.w_tr, self.h_top - 200
        self.net_DL = self.w_tl, self.h_top - 200
        self.net_TR = self.w_tr, self.h_top - 300
        self.net_TL = self.w_tl, self.h_top - 300

        p1_top_left = (self.w_tl + 10, self.h_top + 100)
        p2_top_right = (self.w_tr + 50, self.h_top + 50)
        p3_down_left = (self.w_tl + 50, self.h_top + 350)
        p4_down_right = (self.w_tr + 50, self.h_top + 300)

        # TODO: add intersections and attack lines draw in one function
        # TODO: Draw court net and add the same functionality of moving to its annotations.

        self.intersection1 = self.find_intersection(
            line_pt1=(self.w_tl, self.h_top),
            line_pt2=(self.w_dl, self.h_down),
            x=p1_top_left
        )
        self.intersection2 = self.find_intersection(
            line_pt1=(self.w_tr, self.h_top),
            line_pt2=(self.w_dr, self.h_down),
            x=p2_top_right
        )
        self.intersection3 = self.find_intersection(
            line_pt1=(self.w_tl, self.h_top),
            line_pt2=(self.w_dl, self.h_down),
            x=p3_down_left
        )
        self.intersection4 = self.find_intersection(
            line_pt1=(self.w_tr, self.h_top),
            line_pt2=(self.w_dr, self.h_down),
            x=p4_down_right
        )

        self.root = Tk()
        self.root.title("Court Annotation: ")
        self.canvas = Canvas(self.root, width=self.w + 20, height=self.h + 50, bg='black')
        image = ImageTk.PhotoImage(Image.fromarray(self.frame))
        self.canvas.create_image(0, 0, image=image, anchor="nw")

        # Replace it with draw_court_with_4_points
        self.court_corners()
        self.draw_court()

        # Replace it with draw_court_with_4_points
        self.attack_line_pts()
        self.draw_attack_zone()

        self.canvas.pack()

        self.canvas.bind("<ButtonPress-1>", self.start_move)
        self.canvas.bind("<B1-Motion>", self.move)
        self.root.bind("s", self.save_pts)

        self.root.mainloop()

    def ml_guided_corners(self, frame: NDArray):
        """
        It assists us to find 4 corners of court based on the segmentation model output.
        Args:
            frame:

        Returns:

        """
        points = self.segmentor.predict(frame)
        tl, dl, dr, tr = self.segmentor.find_corners(frame, mask_points=points)
        return tl, dl, dr, tr

    @staticmethod
    def find_intersection(line_pt1: tuple, line_pt2: tuple, x: tuple) -> Tuple[int, int]:
        """
        This method finds the intersection point between point `x` and line
        that connects `line_pt1` and `line_pt2`.
        Args:
            line_pt1:
            line_pt2:
            x:

        Returns:
            the intersection point (x, y)
        """
        line_pt1 = Vector(line_pt1)
        line_pt2 = Vector(line_pt2)
        x = Vector(x)

        intersect = intersect_point_line(x, line_pt1, line_pt2)
        return intersect[0][0], intersect[0][1]

    def draw_court_with_4_points(self, pt1: tuple, pt2: tuple, pt3: tuple, pt4: tuple, color: str) \
            -> Dict[str, List[int]]:
        # Create ovals
        top_left = self.canvas.create_oval(pt1[0], pt1[1], pt1[0] + self.size, pt1[1] + self.size, fill=color)
        down_left = self.canvas.create_oval(pt3[0], pt3[1], pt3[0] + self.size, pt3[1] + self.size, fill=color)
        down_right = self.canvas.create_oval(pt4[0], pt4[1], pt4[0] + self.size, pt4[1] + self.size, fill=color)
        top_right = self.canvas.create_oval(pt2[0], pt2[1], pt2[0] + self.size, pt2[1] + self.size, fill=color)

        # Create lines
        top_line = self.draw_line_pt1_pt2(top_left, top_right, color=color)
        left_line = self.draw_line_pt1_pt2(down_left, top_left, color=color)
        down_line = self.draw_line_pt1_pt2(down_left, down_right, color=color)
        right_line = self.draw_line_pt1_pt2(down_right, top_right, color=color)
        # output everything created
        return {
            "points": [top_left, down_left, down_right, top_right],
            "lines": [top_line, left_line, down_line, right_line]
        }

    def attack_line_pts(self):
        self.att_line_TL = self.canvas.create_oval(
            self.intersection1[0],
            self.intersection1[1],
            self.intersection1[0] + self.size,
            self.intersection1[1] + self.size,
            fill="green"
        )
        self.att_line_TR = self.canvas.create_oval(
            self.intersection2[0],
            self.intersection2[1],
            self.intersection2[0] + self.size,
            self.intersection2[1] + self.size,
            fill="green"
        )

        self.att_line_DL = self.canvas.create_oval(
            self.intersection3[0],
            self.intersection3[1],
            self.intersection3[0] + self.size,
            self.intersection3[1] + self.size,
            fill="green"
        )

        self.att_line_DR = self.canvas.create_oval(
            self.intersection4[0],
            self.intersection4[1],
            self.intersection4[0] + self.size,
            self.intersection4[1] + self.size,
            fill="green"
        )

    def court_corners(self):
        """
        Draws the court corner points.
        Returns:

        """
        self.court_TL = self.canvas.create_oval(
            self.w_tl, self.h_top, self.w_tl + self.size, self.h_top + self.size, fill="red"
        )
        self.court_DL = self.canvas.create_oval(
            self.w_dl, self.h_down, self.w_dl + self.size, self.h_down + self.size, fill="red"
        )
        self.court_TR = self.canvas.create_oval(
            self.w_tr, self.h_top, self.w_tr + self.size, self.h_top + self.size, fill="red"
        )
        self.court_DR = self.canvas.create_oval(
            self.w_dr, self.h_down, self.w_dr + self.size, self.h_down + self.size, fill="red"
        )

    # def net_corners(self):
    #     """
    #     Draws the court corner points.
    #     Returns:
    #
    #     """
    #     self.net_DL = self.canvas.create_oval(
    #         self.w_dl + 100, self.h_down, self.w_dl + self.size, self.h_down + self.size, fill="red"
    #     )
    #     self.net_DR = self.canvas.create_oval(
    #         self.w_dr, self.h_down, self.w_dr + self.size, self.h_down + self.size, fill="red"
    #     )
    #     self.net_TL = self.canvas.create_oval(
    #         self.w_tl, self.h_top, self.w_tl + self.size, self.h_top + self.size, fill="red"
    #     )
    #     self.net_TR = self.canvas.create_oval(
    #         self.w_tr, self.h_top, self.w_tr + self.size, self.h_top + self.size, fill="red"
    #     )

    def draw_court(self):
        self.court_top_line = self.draw_line_pt1_pt2(self.court_TL, self.court_TR, color='red')
        self.court_down_line = self.draw_line_pt1_pt2(self.court_DL, self.court_DR, color='red')
        self.court_left_line = self.draw_line_pt1_pt2(self.court_DL, self.court_TL, color='red')
        self.court_right_line = self.draw_line_pt1_pt2(self.court_DR, self.court_TR, color='red')

    def draw_attack_zone(self):
        self.attackline_top_line = self.draw_line_pt1_pt2(self.att_line_TL, self.att_line_TR, color='green')
        self.attackline_down_line = self.draw_line_pt1_pt2(self.att_line_DL, self.att_line_DR, color='green')
        self.attackline_left_line = self.draw_line_pt1_pt2(self.att_line_DL, self.att_line_TL, color='green')
        self.attackline_right_line = self.draw_line_pt1_pt2(self.att_line_DR, self.att_line_TR, color='green')

        TL = self.canvas.coords(self.att_line_TL)
        DL = self.canvas.coords(self.att_line_DL)
        TR = self.canvas.coords(self.att_line_TR)
        DR = self.canvas.coords(self.att_line_DR)

        TL_pt = self.get_center(TL)
        DL_pt = self.get_center(DL)
        TR_pt = self.get_center(TR)
        DR_pt = self.get_center(DR)

        left = int((TL_pt[0] + DL_pt[0]) / 2), int((TL_pt[1] + DL_pt[1]) / 2)
        right = int((TR_pt[0] + DR_pt[0]) / 2), int((TR_pt[1] + DR_pt[1]) / 2)

        self.center_line = self.draw_line_pt1_pt2(left, right, color='yellow')

    def get_frame(self):
        """
        Selects a frame from video input.
        Returns:

        """
        n_frames = int(self.cap.get(7))
        fno = random.randint(1, n_frames)
        self.cap.set(1, fno)
        _, frame = self.cap.read()
        image = cv2.cvtColor(frame, 4)
        return image

    def draw_line_pt1_pt2(self, pt1: int | Tuple[int, int], pt2: int | Tuple[int, int], color: str):
        """
        It creates a line between `pt1` and `pt2`.

        Args:
            pt1:
            pt2:
            color:

        Returns:

        """
        if isinstance(pt1, int):
            coordination1 = self.canvas.coords(pt1)
            x0 = (coordination1[0] + coordination1[2]) // 2
            y0 = (coordination1[1] + coordination1[3]) // 2
        else:
            x0 = pt1[0]
            y0 = pt1[1]

        if isinstance(pt2, int):
            coordination2 = self.canvas.coords(pt2)
            x1 = (coordination2[0] + coordination2[2]) // 2
            y1 = (coordination2[1] + coordination2[3]) // 2
        else:
            x1 = pt2[0]
            y1 = pt2[1]
        return self.canvas.create_line(x0, y0, x1, y1, fill=color, width=3)

    def reset_lines(self):
        for item in [self.court_top_line, self.court_down_line,
                     self.court_left_line, self.court_right_line]:
            self.canvas.delete(item)
        self.draw_court()
        for item in [
            self.attackline_top_line,
            self.attackline_down_line,
            self.attackline_left_line,
            self.attackline_right_line,
            self.center_line
        ]:
            self.canvas.delete(item)
        self.draw_attack_zone()

    def start_move(self, event):
        self._x = event.x
        self._y = event.y

    def move(self, event):
        """
        Function to call when trying to move the circles around the image
        Args:
            event:

        Returns:

        """
        delta_x = event.x - self._x
        delta_y = event.y - self._y
        self._x = event.x
        self._y = event.y
        self.canvas.move("current", delta_x, delta_y)
        self.reset_lines()

    @staticmethod
    def get_center(pt) -> List[int]:
        return [(pt[0] + pt[2]) // 2, (pt[1] + pt[3]) // 2]

    def save_pts(self, _event=None):
        print("saving coordination....")
        p0 = self.canvas.coords(self.court_TL)
        p1 = self.canvas.coords(self.court_DL)
        p2 = self.canvas.coords(self.court_TR)
        p3 = self.canvas.coords(self.court_DR)
        pt1 = self.get_center(p0)
        pt2 = self.get_center(p1)
        pt3 = self.get_center(p2)
        pt4 = self.get_center(p3)
        court_top_left, court_down_left, court_down_right, court_top_right = self.segmentor.find_corners(
            frame=self.frame,
            mask_points=[pt1, pt2, pt3, pt4]
        )

        p0 = self.canvas.coords(self.att_line_TL)
        p1 = self.canvas.coords(self.att_line_DL)
        p2 = self.canvas.coords(self.att_line_TR)
        p3 = self.canvas.coords(self.att_line_DR)
        pt1 = self.get_center(p0)
        pt2 = self.get_center(p1)
        pt3 = self.get_center(p2)
        pt4 = self.get_center(p3)
        att_top_left, att_down_left, att_down_right, att_top_right = self.segmentor.find_corners(
            frame=self.frame,
            mask_points=[pt1, pt2, pt3, pt4]
        )
        out_dict = {
            "main_zone": [court_top_left, court_down_left, court_down_right, court_top_right],
            "front_zone": [att_top_left, att_down_left, att_down_right, att_top_right]
        }
        json.dump(out_dict, open('output_json.json', 'w'))


if __name__ == '__main__':
    """
    1. select an initial frame from video which can be random
    2. Use a button to change to another frame in the video if current one was unclear.
    3. keep the previous frame numbers, so we can use another button to get to previous ones.

    UI:
        1. insert 4 red points for the whole court annotation.
        2. insert 4 blue points for front zone annotation.

    After annotation:
        1. we get center line.
        2. we get attack lines.
        3. we get front zone of team A, and team B.
        4. we get each 1 - 6 zones for both teams.

    """

    file = '/home/masoud/Desktop/projects/volleyball_analytics/data/raw/videos/train/11.mp4'
    CourtAnnotator(filename=file)

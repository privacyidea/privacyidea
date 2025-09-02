import { ComponentFixture, TestBed } from "@angular/core/testing";

import { SimpleDialogComponent } from "./simple-dialog.component";
import { MAT_DIALOG_DATA } from "@angular/material/dialog";

describe("SimpleDialogComponent", () => {
  let component: SimpleDialogComponent;
  let fixture: ComponentFixture<SimpleDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SimpleDialogComponent],
      providers: [ { provide: MAT_DIALOG_DATA, useValue: {} } ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(SimpleDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});

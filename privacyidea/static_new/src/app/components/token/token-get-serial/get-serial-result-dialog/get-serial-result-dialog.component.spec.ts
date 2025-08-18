import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";

import { GetSerialResultDialogComponent, GetSerialResultDialogData } from "./get-serial-result-dialog.component";

describe("GetSerialResultDialogComponent", () => {
  let component: GetSerialResultDialogComponent;
  let fixture: ComponentFixture<GetSerialResultDialogComponent>;

  const mockDialogRef = { close: jest.fn() };

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [GetSerialResultDialogComponent],
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            serial_list: ["Mock serial"]
          } as unknown as GetSerialResultDialogData
        },
        {
          provide: MatDialogRef,
          useValue: mockDialogRef
        }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(GetSerialResultDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should call dialogRef.close() when you invoke close()", () => {
    component.dialogRef.close("some value");
    expect(mockDialogRef.close).toHaveBeenCalledWith("some value");
  });
});

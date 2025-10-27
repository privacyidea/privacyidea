import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ContainerRegistrationFinalizeDialogComponent } from "./container-registration-finalize-dialog.component";
import { MAT_DIALOG_DATA } from "@angular/material/dialog";
import { By } from "@angular/platform-browser";
import { NO_ERRORS_SCHEMA, signal } from "@angular/core";
import { provideHttpClient } from "@angular/common/http";

const detectChangesStable = async (fixture: ComponentFixture<any>) => {
  fixture.detectChanges();
  await Promise.resolve();
  fixture.detectChanges();
};


describe("ContainerRegistrationFinalizeDialogComponent", () => {
  let component: ContainerRegistrationFinalizeDialogComponent;
  let fixture: ComponentFixture<ContainerRegistrationFinalizeDialogComponent>;
  let mockRegisterContainer: jest.Mock;

  const mockData = signal({
    rollover: false,
    response: {
      result: {
        value: {
          container_url: {
            img: "test-img-url",
            value: "test-link"
          }
        }
      }
    },
    registerContainer: jest.fn()
  });

  beforeEach(async () => {
    await TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [ContainerRegistrationFinalizeDialogComponent],
      providers: [
        provideHttpClient(),
        { provide: MAT_DIALOG_DATA, useValue: mockData }
      ],
      schemas: [NO_ERRORS_SCHEMA]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerRegistrationFinalizeDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    mockRegisterContainer = mockData().registerContainer;
  });

  it("should create", () => {
    expect(component).toBeDefined();
  });

  it("should render 'Register Container' title when not rollover", () => {
    const title = fixture.nativeElement.querySelector("h2");
    expect(title.textContent).toContain("Register Container");
  });

  it("should render 'Container Rollover' title when rollover is true", async () => {
    const rolloverData = signal({ ...mockData(), rollover: true });
    await TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [ContainerRegistrationFinalizeDialogComponent],
      providers: [
        provideHttpClient(),
        { provide: MAT_DIALOG_DATA, useValue: rolloverData }
      ],
      schemas: [NO_ERRORS_SCHEMA]
    }).compileComponents();
    fixture = TestBed.createComponent(ContainerRegistrationFinalizeDialogComponent);
    component = fixture.componentInstance;
    await detectChangesStable(fixture);
    const titles = fixture.nativeElement.querySelectorAll("h2");
    const titleText = Array.from(titles).map((el: any) => el.textContent.trim()).join(" ");
    expect(titleText).toContain("Container Rollover");
  });

  it("should display QR code image if present", () => {
    const img = fixture.nativeElement.querySelector("img.qr-code");
    expect(img).not.toBeNull();
    expect(img.src).toContain("test-img-url");
  });

  it("should display registration link", () => {
    const link = fixture.nativeElement.querySelector("a");
    expect(link).not.toBeNull();
    expect(link.href).toContain("test-link");
  });

  it("should call registerContainer with correct arguments when regenerateQRCode is called", () => {
    component.regenerateQRCode();
    expect(mockRegisterContainer).toHaveBeenCalledWith(undefined, undefined, undefined, false, true);
  });

  it("should call regenerateQRCode when button is clicked", () => {
    const button = fixture.debugElement.query(By.css("button.card-button"));
    button.triggerEventHandler("click");
    expect(mockRegisterContainer).toHaveBeenCalled();
  });
});

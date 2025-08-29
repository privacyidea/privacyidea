import { ComponentFixture, TestBed } from "@angular/core/testing";
import "@angular/localize/init";
import { EnrollRadiusComponent } from "./enroll-radius.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";

describe("EnrollRadiusComponent", () => {
  let component: EnrollRadiusComponent;
  let fixture: ComponentFixture<EnrollRadiusComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollRadiusComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollRadiusComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});

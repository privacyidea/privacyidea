import { ComponentFixture, TestBed } from "@angular/core/testing";
import "@angular/localize/init";
import { EnrollPaperComponent } from "./enroll-paper.component";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

describe("EnrollPaperComponent", () => {
  let component: EnrollPaperComponent;
  let fixture: ComponentFixture<EnrollPaperComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollPaperComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollPaperComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});

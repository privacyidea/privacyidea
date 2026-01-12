import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PasswdResolverComponent } from './passwd-resolver.component';
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ComponentRef } from "@angular/core";

describe('PasswdResolverComponent', () => {
  let component: PasswdResolverComponent;
  let componentRef: ComponentRef<PasswdResolverComponent>;
  let fixture: ComponentFixture<PasswdResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PasswdResolverComponent, NoopAnimationsModule]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PasswdResolverComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should emit additionalFormFieldsChange on init', () => {
    const spy = jest.spyOn(component.additionalFormFieldsChange, 'emit');
    component.ngOnInit();
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({
      fileName: component.filenameControl
    }));
  });

  it('should update controls when data input changes', () => {
    componentRef.setInput('data', {
      fileName: '/etc/passwd'
    });

    fixture.detectChanges();

    expect(component.filenameControl.value).toBe('/etc/passwd');
  });
});

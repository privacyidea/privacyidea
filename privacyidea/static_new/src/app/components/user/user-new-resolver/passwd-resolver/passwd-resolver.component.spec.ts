import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PasswdResolverComponent } from './passwd-resolver.component';

describe('PasswdResolverComponent', () => {
  let component: PasswdResolverComponent;
  let fixture: ComponentFixture<PasswdResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PasswdResolverComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PasswdResolverComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

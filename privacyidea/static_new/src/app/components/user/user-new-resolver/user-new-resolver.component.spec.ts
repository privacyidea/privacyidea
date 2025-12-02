import { ComponentFixture, TestBed } from '@angular/core/testing';

import { UserNewResolverComponent } from './user-new-resolver.component';

describe('UserNewResolverComponent', () => {
  let component: UserNewResolverComponent;
  let fixture: ComponentFixture<UserNewResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserNewResolverComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(UserNewResolverComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
